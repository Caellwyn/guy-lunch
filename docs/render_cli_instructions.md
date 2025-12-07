# The Render CLI

Use the Render CLI to manage your Render services and datastores directly from your terminal:

[video]

Among many other capabilities, the CLI supports:

- Triggering service deploys, restarts, and one-off jobs
- Opening a psql session to your database
- Viewing and filtering live service logs

The CLI also supports [non-interactive use](#non-interactive-mode) in scripts and CI/CD.

> Please submit bugs and feature requests on the CLI's [public GitHub repository](https://github.com/render-oss/cli).

## Setup

### 1. Install

**Homebrew**

Run the following commands:

```shell
brew update
brew install render
```

**Linux/MacOS**

Run the following command:

```shell
curl -fsSL https://raw.githubusercontent.com/render-oss/cli/refs/heads/main/bin/install.sh | sh
```

**Direct download**

1. Open the CLI's [GitHub releases page](https://github.com/render-oss/cli/releases/).
2. Download the executable that corresponds to your system's architecture.

If you use an architecture besides those provided, you can build from source instead.

**Build from source**

> We recommend building from source only if no other installation method works for your system.

1. [Install the Go programming language](https://golang.org/doc/install) if you haven't already.

2. Clone and build the CLI project with the following commands:

   ```shell
   git clone git@github.com:render-oss/cli.git
   cd cli
   go build -o render
   ```

After installation completes, open a new terminal tab and run `render` with no arguments to confirm.

### 2. Log in

The Render CLI uses a **CLI token** to authenticate with the Render platform. Generate a token with the following steps:

1. Run the following command:

   ```shell
   render login
   ```

   Your browser opens a confirmation page in the Render Dashboard.

2. Click **Generate token**.

   The CLI saves the generated token to its [local configuration file](#local-config).

3. When you see the success message in your browser, close the tab and return to your terminal.

4. The CLI prompts you to set your active workspace.

   You can switch workspaces at any time with `render workspace set`.

You're ready to go!

## Common commands

> **This is not an exhaustive list of commands.**
>
> - Run `render` with no arguments for a list of all available commands.
> - Run `render help <command>` for details about a specific command.

| Command | Description |
|--------|--------|
| `login` | Opens your browser to authorize the Render CLI for your account. Authorizing generates a CLI token that's saved locally. If the CLI already has a valid CLI token or [API key](#1-authenticate-via-api-key), this command instead exits with a zero status. |
| `workspace set` | Sets the CLI's active workspace. CLI commands always operate on the active workspace. |
| `services` | Lists all services and datastores in the active workspace. Select a service to perform actions like deploying, viewing logs, or opening an SSH/psql session. |
| `deploys list`<br/>`[SERVICE_ID]` | Lists deploys for the specified service. Select a deploy to view its logs or open its details in the Render Dashboard. If you don't provide a service ID in interactive mode, the CLI prompts you to select a service. |
| `deploys create`<br/>`[SERVICE_ID]` | Triggers a deploy for the specified service. If you don't provide a service ID in interactive mode, the CLI prompts you to select a service. In [non-interactive mode](#non-interactive-mode), helpful options include: - `--wait` to block until the deploy completes (a failed deploy exits with a non-zero status) - `--commit [SHA]` to deploy a specific commit (Git-backed services only) - `--image [URL]` to deploy a specific Docker image tag or digest (image-backed services only) |
| `psql`<br/>`[DATABASE_ID]` | Opens a psql session to the specified PostgreSQL database. If you don't provide a database ID in interactive mode, the CLI prompts you to select a database. |
| `ssh`<br/>`[SERVICE_ID]` | Opens an SSH session to a running instance of the specified service. If you don't provide a service ID in interactive mode, the CLI prompts you to select a service. |

## Non-interactive mode

By default, the Render CLI uses interactive, menu-based navigation. This default is great for manual use, but not for scripting or automation.

Configure the CLI for non-interactive use in CI/CD and other automated environments with the following steps:

### 1. Authenticate via API key

The Render CLI can authenticate using an API key instead of [`render login`](#2-log-in). Unlike CLI tokens, API keys do not periodically expire. For security, use this authentication method only for automated environments.

1. Generate an API key with [these steps](api#1-create-an-api-key).

2. In your automation's environment, set the `RENDER_API_KEY` environment variable to your API key:

   ```bash
   export RENDER_API_KEY=rnd_RUExip…
   ```

> If you provide an API key this way, it always takes precedence over CLI tokens you generate with `render login`.

### 2. Set non-interactive command options

Set the following options for _all_ commands you run in non-interactive mode:

| Flag | Description |
|--------|--------|
| `-o` / `--output` | Sets the output format. For automated environments, specify `json` or `yaml`. Also supports `text` for unstructured text output, along with the default value `interactive`. |
| `--confirm` | Skips any confirmation prompts that the command would otherwise display. |

For example, to list the active workspace's services in JSON format:

```shell
render services --output json --confirm
```

### Example: GitHub Actions

This example action provides similar functionality to Render's [automatic Git deploys](deploys#automatic-git-deploys). You could disable auto-deploys and customize this action to trigger deploys with different conditions.

To use this action, first set the following secrets in your repository:

| Secret              | Description                                        |
| ------------------- | -------------------------------------------------- |
| `RENDER_API_KEY`    | A valid Render [API key](api#1-create-an-api-key) |
| `RENDER_SERVICE_ID` | The ID of the service you want to deploy           |

```yaml
name: Render CLI Deploy
run-name: Deploying via Render CLI
# Run this workflow when code is pushed to the main branch.
on:
  push:
    branches:
      - main
jobs:
  Deploy-Render:
    runs-on: ubuntu-latest
    steps:
      # Downloads the Render CLI binary and adds it to the PATH.
      # To prevent breaking changes in CI/CD, we pin to a
      # specific CLI version (in this case 1.1.0).
      - name: Install Render CLI
        run: |
          curl -L https://github.com/render-oss/cli/releases/download/v1.1.0/cli_1.1.0_linux_amd64.zip -o render.zip
          unzip render.zip
          sudo mv cli_v1.1.0 /usr/local/bin/render
      - name: Trigger deploy with Render CLI
        env:
          # The CLI can authenticate via a Render API key without logging in.
          RENDER_API_KEY: ${{ secrets.RENDER_API_KEY }}
          CI: true
        run: |
          render deploys create ${{ secrets.RENDER_SERVICE_ID }} --output json --confirm
```

## Local config

By default, the Render CLI stores its local configuration at the following path:

```
$HOME/.render/cli.yaml
```

You can change this file path by setting the `RENDER_CLI_CONFIG_PATH` environment variable.

## Managing CLI tokens

For security, CLI tokens periodically expire. If you don't use the Render CLI for a while, you might need to re-authenticate with `render login`.

View a list of your active CLI tokens from your [Account Settings page](https://dashboard.render.com/u/settings#render-cli-tokens) in the Render Dashboard. You can manually revoke a CLI token that you no longer need or that might be compromised. Expired and revoked tokens tokens do not appear in the list.