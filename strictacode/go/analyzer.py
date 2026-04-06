"""
package main

import (
    "encoding/json"
    "fmt"
    "go/ast"
    "go/parser"
    "go/token"
    "log"
    "os"
    "path/filepath"
    "sort"
    "strings"
)

//
// ==============================
// Configuration
// ==============================
var (
    ExcludeDirs = []string{
        ".git",
        "vendor",
    }

    ExcludeFilePrefixes = []string{}
    ExcludeFileSuffixes = []string{
        "_test.go",
    }
)

//
// ==============================
// JSON Models
// ==============================
type Edge struct {
    Source string `json:"source"`
    Target string `json:"target"`
}

type GraphData struct {
    Nodes []string `json:"nodes"`
    Edges []Edge   `json:"edges"`
}

//
// ==============================
// Analyzer
// ==============================
type Analyzer struct {
    fset       *token.FileSet
    nodes      map[string]bool
    edges      []Edge
    structs    map[string]map[string]bool  // file:struct -> method set
    interfaces map[string]map[string]bool  // file:interface -> method set
    typeUsage  map[string]map[string]bool  // file:struct -> set of used type names
}

func NewAnalyzer() *Analyzer {
    return &Analyzer{
        fset:       token.NewFileSet(),
        nodes:      make(map[string]bool),
        edges:      make([]Edge, 0),
        structs:    make(map[string]map[string]bool),
        interfaces: make(map[string]map[string]bool),
        typeUsage:  make(map[string]map[string]bool),
    }
}

//
// ==============================
// File Analysis
// ==============================
func (a *Analyzer) analyzeFile(path, root string) {
    file, err := parser.ParseFile(a.fset, path, nil, parser.ParseComments)
    if err != nil {
        return
    }

    rel, err := filepath.Rel(root, path)
    if err != nil {
        rel = filepath.Base(path)
    }
    rel = filepath.ToSlash(rel)

    for _, decl := range file.Decls {
        switch d := decl.(type) {
        case *ast.GenDecl:
            for _, spec := range d.Specs {
                ts, ok := spec.(*ast.TypeSpec)
                if !ok {
                    continue
                }

                nodeKey := fmt.Sprintf("%s:%s", rel, ts.Name.Name)
                a.nodes[nodeKey] = true

                switch t := ts.Type.(type) {
                case *ast.StructType:
                    // Collect struct methods
                    a.structs[nodeKey] = make(map[string]bool)
                    // Collect embedded types
                    if t.Fields != nil {
                        for _, field := range t.Fields.List {
                            if len(field.Names) == 0 {
                                // Embedded field
                                typeName := a.getTypeName(field.Type)
                                if typeName != "" {
                                    targetKey := fmt.Sprintf("%s:%s", rel, typeName)
                                    a.edges = append(a.edges, Edge{
                                        Source: nodeKey,
                                        Target: targetKey,
                                    })
                                }
                            }
                        }
                    }

                case *ast.InterfaceType:
                    // Collect interface methods
                    a.interfaces[nodeKey] = make(map[string]bool)
                    if t.Methods != nil {
                        for _, method := range t.Methods.List {
                            switch ft := method.Type.(type) {
                            case *ast.FuncType:
                                sig := a.methodSignature(ft)
                                a.interfaces[nodeKey][sig] = true
                            case *ast.Ident:
                                // Embedded interface
                                a.edges = append(a.edges, Edge{
                                    Source: nodeKey,
                                    Target: fmt.Sprintf("%s:%s", rel, ft.Name),
                                })
                            }
                        }
                    }
                }
            }

        case *ast.FuncDecl:
            if d.Recv != nil {
                structName := receiverName(d.Recv)
                if structName == "" {
                    continue
                }
                nodeKey := fmt.Sprintf("%s:%s", rel, structName)
                if _, ok := a.structs[nodeKey]; ok {
                    sig := a.methodSignature(d.Type)
                    a.structs[nodeKey][sig] = true
                }
            }
        }
    }
}

//
// ==============================
// Type Name Extraction
// ==============================
func (a *Analyzer) getTypeName(expr ast.Expr) string {
    switch t := expr.(type) {
    case *ast.Ident:
        return t.Name
    case *ast.StarExpr:
        return a.getTypeName(t.X)
    case *ast.SelectorExpr:
        return t.Sel.Name
    }
    return ""
}

//
// ==============================
// Method Signature
// ==============================
func (a *Analyzer) methodSignature(ft *ast.FuncType) string {
    var sb strings.Builder

    // Parameters
    sb.WriteString("(")
    if ft.Params != nil {
        params := make([]string, 0)
        for _, p := range ft.Params.List {
            params = append(params, a.typeString(p.Type))
        }
        sb.WriteString(strings.Join(params, ","))
    }
    sb.WriteString(")")

    // Results
    sb.WriteString("(")
    if ft.Results != nil {
        results := make([]string, 0)
        for _, r := range ft.Results.List {
            results = append(results, a.typeString(r.Type))
        }
        sb.WriteString(strings.Join(results, ","))
    }
    sb.WriteString(")")

    return sb.String()
}

func (a *Analyzer) typeString(expr ast.Expr) string {
    switch t := expr.(type) {
    case *ast.Ident:
        return t.Name
    case *ast.StarExpr:
        return "*" + a.typeString(t.X)
    case *ast.ArrayType:
        return "[]" + a.typeString(t.Elt)
    case *ast.SelectorExpr:
        return t.Sel.Name
    case *ast.MapType:
        return "map[" + a.typeString(t.Key) + "]" + a.typeString(t.Value)
    case *ast.InterfaceType:
        return "interface{}"
    case *ast.Ellipsis:
        return "..." + a.typeString(t.Elt)
    case *ast.ChanType:
        return "chan " + a.typeString(t.Value)
    case *ast.FuncType:
        return "func" + a.methodSignature(t)
    }
    return "unknown"
}

//
// ==============================
// Interface Implementation Check
// ==============================
func (a *Analyzer) checkInterfaceImplementation() {
    for structKey, structMethods := range a.structs {
        for ifaceKey, ifaceMethods := range a.interfaces {
            if a.implements(structMethods, ifaceMethods) {
                a.edges = append(a.edges, Edge{
                    Source: structKey,
                    Target: ifaceKey,
                })
            }
        }
    }
}

func (a *Analyzer) implements(structMethods, ifaceMethods map[string]bool) bool {
    for sig := range ifaceMethods {
        if !structMethods[sig] {
            return false
        }
    }
    return true
}

//
// ==============================
// Type Usage Detection
// ==============================
var baseTypes = map[string]bool{
    "bool": true, "string": true, "error": true, "any": true,
    "int": true, "int8": true, "int16": true, "int32": true, "int64": true,
    "uint": true, "uint8": true, "uint16": true, "uint32": true, "uint64": true,
    "float32": true, "float64": true,
    "byte": true, "rune": true,
}

func (a *Analyzer) addUsage(owner, typeName string) {
    if baseTypes[typeName] {
        return
    }
    if _, ok := a.typeUsage[owner]; !ok {
        a.typeUsage[owner] = make(map[string]bool)
    }
    a.typeUsage[owner][typeName] = true
}

func (a *Analyzer) collectTypeFromExpr(owner string, expr ast.Expr) {
    name := a.getTypeName(expr)
    if name != "" {
        a.addUsage(owner, name)
    }
}

func (a *Analyzer) collectTypesFromFieldList(owner string, fl *ast.FieldList) {
    if fl == nil {
        return
    }
    for _, field := range fl.List {
        a.collectTypeFromExpr(owner, field.Type)
    }
}

func (a *Analyzer) collectUsageFromFile(path, root string) {
    file, err := parser.ParseFile(a.fset, path, nil, parser.ParseComments)
    if err != nil {
        return
    }

    rel, err := filepath.Rel(root, path)
    if err != nil {
        rel = filepath.Base(path)
    }
    rel = filepath.ToSlash(rel)

    for _, decl := range file.Decls {
        switch d := decl.(type) {
        case *ast.GenDecl:
            for _, spec := range d.Specs {
                ts, ok := spec.(*ast.TypeSpec)
                if !ok {
                    continue
                }
                st, ok := ts.Type.(*ast.StructType)
                if !ok {
                    continue
                }
                nodeKey := fmt.Sprintf("%s:%s", rel, ts.Name.Name)
                // Collect type usage from struct fields (named fields only;
                // unnamed/embedded are already handled as inheritance edges)
                if st.Fields != nil {
                    for _, field := range st.Fields.List {
                        if len(field.Names) > 0 {
                            a.collectTypeFromExpr(nodeKey, field.Type)
                        }
                    }
                }
            }

        case *ast.FuncDecl:
            if d.Recv == nil {
                continue
            }
            structName := receiverName(d.Recv)
            if structName == "" {
                continue
            }
            nodeKey := fmt.Sprintf("%s:%s", rel, structName)
            if _, ok := a.nodes[nodeKey]; !ok {
                continue
            }

            // Params and results
            a.collectTypesFromFieldList(nodeKey, d.Type.Params)
            a.collectTypesFromFieldList(nodeKey, d.Type.Results)

            // Body: var declarations and composite literals
            if d.Body != nil {
                ast.Inspect(d.Body, func(n ast.Node) bool {
                    switch node := n.(type) {
                    case *ast.ValueSpec:
                        if node.Type != nil {
                            a.collectTypeFromExpr(nodeKey, node.Type)
                        }
                    case *ast.CompositeLit:
                        if node.Type != nil {
                            a.collectTypeFromExpr(nodeKey, node.Type)
                        }
                    case *ast.CallExpr:
                        // new(T)
                        if ident, ok := node.Fun.(*ast.Ident); ok && ident.Name == "new" && len(node.Args) > 0 {
                            a.collectTypeFromExpr(nodeKey, node.Args[0])
                        }
                    case *ast.UnaryExpr:
                        // &T{...}
                        if node.Op == token.AND {
                            if cl, ok := node.X.(*ast.CompositeLit); ok && cl.Type != nil {
                                a.collectTypeFromExpr(nodeKey, cl.Type)
                            }
                        }
                    }
                    return true
                })
            }
        }
    }
}

func (a *Analyzer) checkTypeUsage() {
    // Build name -> list of node IDs (sorted for determinism)
    nameToNodes := make(map[string][]string)
    for nodeID := range a.nodes {
        parts := strings.SplitN(nodeID, ":", 2)
        if len(parts) == 2 {
            nameToNodes[parts[1]] = append(nameToNodes[parts[1]], nodeID)
        }
    }
    for name := range nameToNodes {
        sort.Strings(nameToNodes[name])
    }

    // Build existing edge set
    existing := make(map[string]bool)
    for _, e := range a.edges {
        key := e.Source + "->" + e.Target
        existing[key] = true
    }

    // Resolve usage to edges — create edge to every matching node
    for owner, types := range a.typeUsage {
        for typeName := range types {
            targets, ok := nameToNodes[typeName]
            if !ok {
                continue
            }
            for _, targetNode := range targets {
                if targetNode == owner {
                    continue
                }
                key := owner + "->" + targetNode
                if existing[key] {
                    continue
                }
                a.edges = append(a.edges, Edge{
                    Source: owner,
                    Target: targetNode,
                })
                existing[key] = true
            }
        }
    }
}

//
// ==============================
// Helpers
// ==============================
func receiverName(fl *ast.FieldList) string {
    if fl == nil || len(fl.List) == 0 {
        return ""
    }

    switch expr := fl.List[0].Type.(type) {
    case *ast.Ident:
        return expr.Name
    case *ast.StarExpr:
        if ident, ok := expr.X.(*ast.Ident); ok {
            return ident.Name
        }
    }
    return ""
}

//
// ==============================
// Output
// ==============================
func (a *Analyzer) toJSON() GraphData {
    nodes := make([]string, 0, len(a.nodes))
    for n := range a.nodes {
        nodes = append(nodes, n)
    }

    return GraphData{
        Nodes: nodes,
        Edges: a.edges,
    }
}

//
// ==============================
// Entry Point
// ==============================
func main() {
    if len(os.Args) < 2 {
        log.Fatal("usage: go run script.go <path-to-analyze>")
    }

    root := os.Args[1]
    rootAbs, err := filepath.Abs(root)
    if err != nil {
        log.Fatal(err)
    }

    analyzer := NewAnalyzer()

    err = filepath.Walk(rootAbs, func(path string, info os.FileInfo, err error) error {
        if err != nil {
            return nil
        }

        if info.IsDir() {
            for _, ex := range ExcludeDirs {
                if info.Name() == ex {
                    return filepath.SkipDir
                }
            }
            return nil
        }

        if !strings.HasSuffix(path, ".go") {
            return nil
        }

        name := info.Name()

        for _, p := range ExcludeFilePrefixes {
            if strings.HasPrefix(name, p) {
                return nil
            }
        }

        for _, s := range ExcludeFileSuffixes {
            if strings.HasSuffix(name, s) {
                return nil
            }
        }

        analyzer.analyzeFile(path, rootAbs)
        return nil
    })

    if err != nil {
        log.Fatal(err)
    }

    analyzer.checkInterfaceImplementation()

    // Type usage detection
    err = filepath.Walk(rootAbs, func(path string, info os.FileInfo, err error) error {
        if err != nil {
            return nil
        }
        if info.IsDir() {
            for _, ex := range ExcludeDirs {
                if info.Name() == ex {
                    return filepath.SkipDir
                }
            }
            return nil
        }
        if !strings.HasSuffix(path, ".go") {
            return nil
        }
        name := info.Name()
        for _, p := range ExcludeFilePrefixes {
            if strings.HasPrefix(name, p) {
                return nil
            }
        }
        for _, s := range ExcludeFileSuffixes {
            if strings.HasSuffix(name, s) {
                return nil
            }
        }
        analyzer.collectUsageFromFile(path, rootAbs)
        return nil
    })
    if err != nil {
        log.Fatal(err)
    }

    analyzer.checkTypeUsage()

    out, err := json.Marshal(analyzer.toJSON())
    if err != nil {
        log.Fatal(err)
    }

    fmt.Println(string(out))
}
"""

import json
import os
import subprocess
import tempfile


def analyze(path: str) -> dict:
    with tempfile.TemporaryDirectory() as tmpdir:
        go_file = os.path.join(tmpdir, "analyzer.go")
        with open(go_file, "w") as f:
            f.write(__doc__)

        cmd = ["go", "run", go_file, path]
        result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(result.stderr)

    return json.loads(result.stdout)
