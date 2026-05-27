from click.testing import CliRunner

from app.cli.main import cli


def test_cli_help_includes_core_groups() -> None:
    result = CliRunner().invoke(cli, ["--help"])

    assert result.exit_code == 0
    for name in [
        "item",
        "location",
        "backup",
        "tag",
        "category",
        "attr-def",
        "system",
        "image",
        "file",
        "note",
        "search",
        "config",
        "ping",
    ]:
        assert name in result.output


def test_item_help_includes_business_actions() -> None:
    result = CliRunner().invoke(cli, ["item", "--help"])

    assert result.exit_code == 0
    for command in [
        "list",
        "show",
        "add",
        "update",
        "delete",
        "move",
        "add-qty",
        "use",
        "adjust",
        "restock",
        "unstock",
        "favorite",
        "unfavorite",
        "tag",
        "untag",
        "alias",
        "unalias",
        "bind",
        "unbind",
        "find-id",
        "notes",
        "add-note",
    ]:
        assert command in result.output


def test_location_help_includes_expected_actions() -> None:
    result = CliRunner().invoke(cli, ["location", "--help"])

    assert result.exit_code == 0
    for command in ["list", "tree", "show", "add", "update", "delete", "items"]:
        assert command in result.output


def test_tag_help_includes_expected_actions() -> None:
    result = CliRunner().invoke(cli, ["tag", "--help"])

    assert result.exit_code == 0
    for command in ["add", "list", "delete"]:
        assert command in result.output


def test_category_help_includes_expected_actions() -> None:
    result = CliRunner().invoke(cli, ["category", "--help"])

    assert result.exit_code == 0
    for command in ["list", "tree", "add", "update", "delete"]:
        assert command in result.output


def test_attr_def_help_includes_expected_actions() -> None:
    result = CliRunner().invoke(cli, ["attr-def", "--help"])

    assert result.exit_code == 0
    for command in ["add", "list", "update", "delete"]:
        assert command in result.output


def test_backup_help_includes_expected_actions() -> None:
    result = CliRunner().invoke(cli, ["backup", "--help"])

    assert result.exit_code == 0
    for command in ["create", "list", "restore", "download"]:
        assert command in result.output


def test_system_help_includes_expected_actions() -> None:
    result = CliRunner().invoke(cli, ["system", "--help"])

    assert result.exit_code == 0
    assert "info" in result.output


def test_file_and_image_commands_registered() -> None:
    result = CliRunner().invoke(cli, ["--help"])

    assert result.exit_code == 0
    for name in ["image", "file"]:
        assert name in result.output


def test_image_help_includes_expected_actions() -> None:
    result = CliRunner().invoke(cli, ["image", "--help"])

    assert result.exit_code == 0
    assert "add" in result.output


def test_file_help_includes_expected_actions() -> None:
    result = CliRunner().invoke(cli, ["file", "--help"])

    assert result.exit_code == 0
    for command in ["add", "list", "delete"]:
        assert command in result.output


def test_note_help_includes_expected_actions() -> None:
    result = CliRunner().invoke(cli, ["note", "--help"])

    assert result.exit_code == 0
    for command in ["add", "list"]:
        assert command in result.output


def test_legacy_flat_file_commands_are_hidden_but_available() -> None:
    help_result = CliRunner().invoke(cli, ["--help"])

    assert help_result.exit_code == 0
    for name in ["image-add", "file-add", "file-list", "file-delete"]:
        assert name not in help_result.output

    command_result = CliRunner().invoke(cli, ["image-add", "--help"])
    assert command_result.exit_code == 0


def test_item_add_accepts_tag_and_attr_options() -> None:
    result = CliRunner().invoke(
        cli,
        ["item", "add", "--help"],
    )
    assert result.exit_code == 0
    assert "--tag" in result.output
    assert "--attr" in result.output
    assert "--status" in result.output


def test_item_list_accepts_tag_and_status_options() -> None:
    result = CliRunner().invoke(cli, ["item", "list", "--help"])
    assert result.exit_code == 0
    assert "--tag" in result.output
    assert "--status" in result.output
