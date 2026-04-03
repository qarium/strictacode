from strictacode.swift.tools import walk_swift_files


class TestWalkSwiftFiles:
    def test_finds_swift_files(self, tmp_path):
        (tmp_path / "a.swift").write_text("")
        (tmp_path / "b.swift").write_text("")

        result = list(walk_swift_files(str(tmp_path)))

        assert len(result) == 2

    def test_ignores_non_swift_files(self, tmp_path):
        (tmp_path / "a.swift").write_text("")
        (tmp_path / "b.py").write_text("")
        (tmp_path / "c.txt").write_text("")

        result = list(walk_swift_files(str(tmp_path)))

        assert len(result) == 1
        assert result[0].endswith("a.swift")

    def test_ignores_test_suffixes(self, tmp_path):
        (tmp_path / "Service.swift").write_text("")
        (tmp_path / "ServiceTest.swift").write_text("")
        (tmp_path / "ServiceSpec.swift").write_text("")
        (tmp_path / "ServiceTests.swift").write_text("")

        result = list(walk_swift_files(str(tmp_path)))

        names = [r.split("/")[-1] for r in result]
        assert names == ["Service.swift"]

    def test_ignores_dirs(self, tmp_path):
        (tmp_path / "a.swift").write_text("")

        build = tmp_path / ".build"
        build.mkdir()
        (build / "Generated.swift").write_text("")

        swiftpm = tmp_path / ".swiftpm"
        swiftpm.mkdir()
        (swiftpm / "Package.swift").write_text("")

        result = list(walk_swift_files(str(tmp_path)))

        assert len(result) == 1
        assert result[0].endswith("a.swift")

    def test_empty_directory(self, tmp_path):
        result = list(walk_swift_files(str(tmp_path)))

        assert result == []

    def test_sorted_output(self, tmp_path):
        (tmp_path / "z.swift").write_text("")
        (tmp_path / "a.swift").write_text("")
        (tmp_path / "m.swift").write_text("")

        result = list(walk_swift_files(str(tmp_path)))
        names = [r.split("/")[-1] for r in result]

        assert names == ["a.swift", "m.swift", "z.swift"]

    def test_nested_directories(self, tmp_path):
        src = tmp_path / "Sources"
        src.mkdir()
        (src / "App.swift").write_text("")

        sub = src / "Models"
        sub.mkdir()
        (sub / "User.swift").write_text("")

        result = list(walk_swift_files(str(tmp_path)))

        assert len(result) == 2
