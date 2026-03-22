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
type Closure struct {
    Type       string    `json:"type"`
    Lineno     int       `json:"lineno"`
    Complexity int       `json:"complexity"`
    Endline    int       `json:"endline"`
    Name       string    `json:"name"`
    Closures   []Closure `json:"closures"`
}

type Method struct {
    Type       string    `json:"type"`
    Lineno     int       `json:"lineno"`
    Complexity int       `json:"complexity"`
    Endline    int       `json:"endline"`
    Name       string    `json:"name"`
    Structure  string    `json:"structure"`
    Closures   []Closure `json:"closures"`
}

type Structure struct {
    Type       string   `json:"type"`
    Lineno     int      `json:"lineno"`
    Complexity int      `json:"complexity"`
    Endline    int      `json:"endline"`
    Name       string   `json:"name"`
    Methods    []Method `json:"methods"`
}

type Function struct {
    Type       string    `json:"type"`
    Lineno     int       `json:"lineno"`
    Complexity int       `json:"complexity"`
    Endline    int       `json:"endline"`
    Name       string    `json:"name"`
    Closures   []Closure `json:"closures"`
}

//
// ==============================
// Analyzer
// ==============================
type Analyzer struct {
    fset *token.FileSet
    data map[string][]interface{}
}

func NewAnalyzer() *Analyzer {
    return &Analyzer{
        fset: token.NewFileSet(),
        data: make(map[string][]interface{}),
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
    rel = filepath.ToSlash(rel) // normalize

    var structures []Structure
    var functions []Function
    methodsByStruct := map[string][]Method{}

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

                start := a.fset.Position(st.Pos()).Line
                end := a.fset.Position(st.End()).Line

                structures = append(structures, Structure{
                    Type:       "structure",
                    Lineno:     start,
                    Complexity: 0, // будет пересчитано ниже
                    Endline:    end,
                    Name:       ts.Name.Name,
                })
            }

        case *ast.FuncDecl:
            if d.Recv != nil {
                structName := receiverName(d.Recv)
                if structName == "" {
                    continue
                }

                method := a.buildMethod(d, structName)
                methodsByStruct[structName] = append(methodsByStruct[structName], method)
            } else {
                functions = append(functions, a.buildFunction(d))
            }
        }
    }

    // attach methods и посчитаем complexity структуры
    for si := range structures {
        structures[si].Methods = methodsByStruct[structures[si].Name]

        // сортировка методов по lineno
        sort.Slice(structures[si].Methods, func(mi, mj int) bool {
            return structures[si].Methods[mi].Lineno < structures[si].Methods[mj].Lineno
        })

        // считаем complexity структуры как сумму всех методов
        total := 0
        for _, m := range structures[si].Methods {
            total += m.Complexity
        }
        structures[si].Complexity = total
    }

    // сортировка структур и функций
    sort.Slice(structures, func(i, j int) bool {
        return structures[i].Lineno < structures[j].Lineno
    })
    sort.Slice(functions, func(i, j int) bool {
        return functions[i].Lineno < functions[j].Lineno
    })

    var combined []interface{}
    for _, s := range structures {
        combined = append(combined, s)
    }
    for _, f := range functions {
        combined = append(combined, f)
    }

    if len(combined) > 0 {
        a.data[rel] = combined
    }
}

//
// ==============================
// Builders
// ==============================
func (a *Analyzer) buildMethod(d *ast.FuncDecl, structName string) Method {
    start := a.fset.Position(d.Pos()).Line
    end := a.fset.Position(d.End()).Line

    return Method{
        Type:       "method",
        Lineno:     start,
        Complexity: computeComplexity(d.Body),
        Endline:    end,
        Name:       d.Name.Name,
        Structure:  structName,
        Closures:   extractClosures(a.fset, d.Body),
    }
}

func (a *Analyzer) buildFunction(d *ast.FuncDecl) Function {
    start := a.fset.Position(d.Pos()).Line
    end := a.fset.Position(d.End()).Line

    return Function{
        Type:       "function",
        Lineno:     start,
        Complexity: computeComplexity(d.Body),
        Endline:    end,
        Name:       d.Name.Name,
        Closures:   extractClosures(a.fset, d.Body),
    }
}

//
// ==============================
// Complexity
// ==============================
func computeComplexity(body *ast.BlockStmt) int {
    if body == nil {
        return 1
    }

    complexity := 1

    ast.Inspect(body, func(n ast.Node) bool {
        switch n.(type) {
        case *ast.FuncLit:
            return false
        case *ast.IfStmt,
            *ast.ForStmt,
            *ast.RangeStmt,
            *ast.GoStmt,
            *ast.DeferStmt:
            complexity++
        case *ast.BinaryExpr:
            be := n.(*ast.BinaryExpr)
            if be.Op.String() == "&&" || be.Op.String() == "||" {
                complexity++
            }
        case *ast.CaseClause:
            cc := n.(*ast.CaseClause)
            if cc.List != nil {
                complexity++
            }
        case *ast.CommClause:
            cc := n.(*ast.CommClause)
            if cc.Comm != nil {
                complexity++
            }
        }
        return true
    })

    return complexity
}

//
// ==============================
// Closures
// ==============================
func extractClosures(fset *token.FileSet, body *ast.BlockStmt) []Closure {
    closures := make([]Closure, 0)
    if body == nil {
        return closures
    }

    ast.Inspect(body, func(n ast.Node) bool {
        fl, ok := n.(*ast.FuncLit)
        if !ok {
            return true
        }

        start := fset.Position(fl.Pos()).Line
        end := fset.Position(fl.End()).Line

        closure := Closure{
            Type:       "function",
            Lineno:     start,
            Complexity: computeComplexity(fl.Body),
            Endline:    end,
            Name:       "closure",
            Closures:   extractClosures(fset, fl.Body),
        }

        closures = append(closures, closure)
        return true
    })

    return closures
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

func (a *Analyzer) printJSON() {
    keys := make([]string, 0, len(a.data))
    for k := range a.data {
        keys = append(keys, k)
    }
    sort.Strings(keys)

    ordered := make(map[string][]interface{})
    for _, k := range keys {
        ordered[k] = a.data[k]
    }

    out, err := json.MarshalIndent(ordered, "", "    ")
    if err != nil {
        log.Fatal(err)
    }

    fmt.Println(string(out))
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

    analyzer.printJSON()
}
"""

import os
import json
import tempfile
import subprocess


def collect(path: str) -> dict:
    with tempfile.TemporaryDirectory() as tmpdir:
        go_file = os.path.join(tmpdir, "collector.go")
        with open(go_file, "w") as f:
            f.write(__doc__)

        cmd = ["go", "run", go_file, path]
        result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(result.stderr)

    return json.loads(result.stdout)
