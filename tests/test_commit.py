import pytest
from typer.testing import CliRunner
from gittask.commands.commit import commit
import typer
import subprocess

runner = CliRunner()

# We need to wrap the function in a Typer app to test it with CliRunner
app = typer.Typer()
app.command()(commit)

def test_commit_success(mock_db, mock_git, mocker):
    """
    Test successful commit.
    """
    mocker.patch("gittask.commands.commit.db", mock_db)
    mocker.patch("gittask.commands.commit.git", mock_git)
    
    mock_subprocess = mocker.patch("gittask.commands.commit.subprocess.run")
    
    result = runner.invoke(app, ["-m", "test commit"])
    
    assert result.exit_code == 0
    assert "Commit successful" in result.stdout
    
    mock_subprocess.assert_called_with(["git", "commit", "-m", "test commit"], check=True)

def test_commit_all_files(mock_db, mock_git, mocker):
    """
    Test commit with -a flag.
    """
    mocker.patch("gittask.commands.commit.db", mock_db)
    mocker.patch("gittask.commands.commit.git", mock_git)
    
    mock_subprocess = mocker.patch("gittask.commands.commit.subprocess.run")
    
    result = runner.invoke(app, ["-m", "test commit", "-a"])
    
    assert result.exit_code == 0
    
    mock_subprocess.assert_called_with(["git", "commit", "-a", "-m", "test commit"], check=True)

def test_commit_failure(mock_db, mock_git, mocker):
    """
    Test commit failure (e.g. git error).
    """
    mocker.patch("gittask.commands.commit.db", mock_db)
    mocker.patch("gittask.commands.commit.git", mock_git)
    
    mock_subprocess = mocker.patch("gittask.commands.commit.subprocess.run")
    mock_subprocess.side_effect = subprocess.CalledProcessError(1, "git commit")
    
    result = runner.invoke(app, ["-m", "test commit"])
    
    assert result.exit_code == 1
