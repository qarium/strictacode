from strictacode.kotlin.tools import walk_kotlin_files


class TestWalkKotlinFiles:
    def test_finds_kotlin_files(self, tmp_path):
        (tmp_path / "a.kt").write_text("")
        (tmp_path / "b.kt").write_text("")

        result = list(walk_kotlin_files(str(tmp_path)))

        assert len(result) == 2

    def test_ignores_non_kotlin_files(self, tmp_path):
        (tmp_path / "a.kt").write_text("")
        (tmp_path / "b.java").write_text("")
        (tmp_path / "c.xml").write_text("")

        result = list(walk_kotlin_files(str(tmp_path)))

        assert len(result) == 1
        assert result[0].endswith("a.kt")

    def test_ignores_test_suffixes(self, tmp_path):
        (tmp_path / "Service.kt").write_text("")
        (tmp_path / "ServiceTest.kt").write_text("")
        (tmp_path / "ServiceSpec.kt").write_text("")
        (tmp_path / "ServiceTests.kt").write_text("")

        result = list(walk_kotlin_files(str(tmp_path)))

        names = [r.split("/")[-1] for r in result]
        assert names == ["Service.kt"]

    def test_ignores_dirs(self, tmp_path):
        (tmp_path / "a.kt").write_text("")

        gradle = tmp_path / ".gradle"
        gradle.mkdir()
        (gradle / "Config.kt").write_text("")

        build = tmp_path / "build"
        build.mkdir()
        (build / "Generated.kt").write_text("")

        idea = tmp_path / ".idea"
        idea.mkdir()
        (idea / "Misc.kt").write_text("")

        result = list(walk_kotlin_files(str(tmp_path)))

        assert len(result) == 1
        assert result[0].endswith("a.kt")

    def test_empty_directory(self, tmp_path):
        result = list(walk_kotlin_files(str(tmp_path)))

        assert result == []

    def test_sorted_output(self, tmp_path):
        (tmp_path / "z.kt").write_text("")
        (tmp_path / "a.kt").write_text("")
        (tmp_path / "m.kt").write_text("")

        result = list(walk_kotlin_files(str(tmp_path)))
        names = [r.split("/")[-1] for r in result]

        assert names == ["a.kt", "m.kt", "z.kt"]

    def test_nested_directories(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "Main.kt").write_text("")

        sub = src / "models"
        sub.mkdir()
        (sub / "User.kt").write_text("")

        result = list(walk_kotlin_files(str(tmp_path)))

        assert len(result) == 2
