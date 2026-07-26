from good_samaritan.contributing import contribution_files, guidance, rejects_automated_contributions


def test_finds_guides_in_root_docs_and_github(tmp_path):
    (tmp_path / "CONTRIBUTE.md").write_text("Run make test.\n")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "contributing.rst").write_text("Format with ruff.\n")
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github" / "CONTRIBUTING.md").write_text("Add a changelog entry.\n")

    assert [path.relative_to(tmp_path).as_posix() for path in contribution_files(tmp_path)] == ["CONTRIBUTE.md", ".github/CONTRIBUTING.md", "docs/contributing.rst"]
    text = guidance(tmp_path)
    assert "Run make test." in text
    assert "Add a changelog entry." in text


def test_only_explicit_automated_contribution_bans_are_rejected():
    assert rejects_automated_contributions("AI generated pull requests are not accepted.")
    assert not rejects_automated_contributions("Please describe any AI assistance in your pull request.")
