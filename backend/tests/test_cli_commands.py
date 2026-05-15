from click.testing import CliRunner

from app.cli.main import cli


def test_cli_help_includes_core_groups() -> None:
    result = CliRunner().invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "item" in result.output
    assert "location" in result.output
    assert "backup" in result.output
    assert "tag" in result.output
    assert "attr-def" in result.output


def test_item_help_includes_business_actions() -> None:
    result = CliRunner().invoke(cli, ["item", "--help"])

    assert result.exit_code == 0
    for command in [
        "move",
        "add-qty",
        "use",
        "adjust",
        "restock",
        "favorite",
        "tag",
        "alias",
        "bind",
        "find-id",
    ]:
        assert command in result.output


def test_location_help_includes_expected_actions() -> None:
    result = CliRunner().invoke(cli, ["location", "--help"])

    assert result.exit_code == 0
    for command in ["add", "list", "tree"]:
        assert command in result.output


def test_tag_help_includes_expected_actions() -> None:
    result = CliRunner().invoke(cli, ["tag", "--help"])

    assert result.exit_code == 0
    for command in ["add", "list"]:
        assert command in result.output


def test_attr_def_help_includes_expected_actions() -> None:
    result = CliRunner().invoke(cli, ["attr-def", "--help"])

    assert result.exit_code == 0
    for command in ["add", "list"]:
        assert command in result.output
