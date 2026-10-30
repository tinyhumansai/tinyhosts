"""Contract tests for the reviewed TinyHosts release route."""

import os
import re
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ReviewedReleaseContractTests(unittest.TestCase):
    def test_release_manifest_and_tinybus_sdk_are_pinned_together(self):
        manifest = tomllib.loads((ROOT / "Cargo.toml").read_text())
        bus_manifest = tomllib.loads((ROOT / "crates" / "tinyhosts-bus" / "Cargo.toml").read_text())
        self.assertEqual(manifest["package"]["version"], "0.4.2")
        self.assertEqual(bus_manifest["package"]["version"], "0.4.2")
        self.assertEqual(manifest["dependencies"]["tinyhosts-bus"]["version"], "0.4.2")
        self.assertEqual(manifest["dependencies"]["tinybus"]["version"], ">=0.3.3, <0.4")
        self.assertEqual(manifest["dependencies"]["tinybus-module"]["version"], ">=0.3.3, <0.4")
        self.assertEqual(
            subprocess.check_output(
                ["git", "-C", str(ROOT), "rev-parse", "HEAD:vendor/tinybus"], text=True
            ).strip(),
            "207a9a7df15e44fdba00a807d0f7eaf21904ba0e",
        )

    def test_reviewed_epic_release_delegates_to_the_canonical_preflight(self):
        workflow = (ROOT / ".github" / "workflows" / "release-reviewed-epic.yml").read_text()
        inputs = workflow.split("    inputs:\n", 1)[1].split("\npermissions:", 1)[0]
        self.assertEqual(
            re.findall(r"^      ([a-z-]+):$", inputs, re.MULTILINE),
            ["tag", "version", "reviewed-pr"],
        )
        self.assertIn("      tag:\n        description:", inputs)
        self.assertIn("      version:\n        description:", inputs)
        self.assertIn("      reviewed-pr:\n        description:", inputs)
        self.assertEqual(inputs.count("        type: string"), 2)
        self.assertIn("        type: number", inputs)
        self.assertIn("canonical epic branch", workflow)
        self.assertIn(
            "permissions:\n  contents: write\n  pull-requests: read\n  checks: read\n  actions: read\n",
            workflow,
        )
        self.assertIn(
            "uses: tinyhumansai/.github/.github/workflows/module-reviewed-epic-release.yml"
            "@6ed83b04aab2d8977ec62e966cb914531e534fa4",
            workflow,
        )
        self.assertIn("tag: ${{ inputs.tag }}", workflow)
        self.assertIn("version: ${{ inputs.version }}", workflow)
        self.assertIn("reviewed-pr: ${{ inputs['reviewed-pr'] }}", workflow)
        self.assertNotIn("module-crate:", workflow)
        self.assertNotIn("actions/checkout", workflow)
        self.assertNotIn("validate_reviewed_release.py", workflow)
        self.assertNotIn("  push:", workflow)

    def test_registered_release_dispatch_routes_reviewed_epics_to_preflight(self):
        workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text()
        dispatch = re.search(
            r"(?ms)^  workflow_dispatch:\n(?P<body>.*?)(?=^  push:)", workflow
        )
        self.assertIsNotNone(dispatch)
        inputs = dispatch.group("body")
        self.assertRegex(
            inputs,
            r"(?ms)^    inputs:\n.*?^      release_mode:\n"
            r"(?:(?!^      [a-z-]+:).)*?^        type: choice\n"
            r"(?:(?!^      [a-z-]+:).)*?^        options:\n"
            r"(?:(?!^      [a-z-]+:).)*?^          - main\n"
            r"(?:(?!^      [a-z-]+:).)*?^          - reviewed-epic\n"
            r"(?:(?!^      [a-z-]+:).)*?^        default: main\n",
        )
        self.assertRegex(
            inputs,
            r"(?ms)^      reviewed_pr:\n(?:(?!^      [a-z_]+:).)*?"
            r"^        type: number\n(?:(?!^      [a-z-]+:).)*?"
            r"^        required: false\n",
        )
        self.assertIn('[[ "$MODE" == "main" || "$MODE" == "reviewed-epic" ]]', workflow)
        self.assertIn('[[ "$REVIEWED_PR" =~ ^[1-9][0-9]*$ ]]', workflow)
        self.assertIn('echo "mode=$MODE"', workflow)
        self.assertIn('echo "reviewed_pr=$REVIEWED_PR"', workflow)
        self.assertIn('} >> "$GITHUB_OUTPUT"', workflow)

        reviewed_job = re.search(
            r"(?ms)^  reviewed-module-release:\n(?P<body>.*?)(?=^  [a-z0-9-]+:|\Z)",
            workflow,
        )
        self.assertIsNotNone(reviewed_job)
        self.assertIn(
            "if: needs.resolve.outputs.mode == 'reviewed-epic'",
            reviewed_job.group("body"),
        )
        self.assertIn(
            "uses: tinyhumansai/.github/.github/workflows/module-reviewed-epic-release.yml"
            "@6ed83b04aab2d8977ec62e966cb914531e534fa4",
            reviewed_job.group("body"),
        )
        self.assertIn("pull-requests: read", reviewed_job.group("body"))
        self.assertIn("checks: read", reviewed_job.group("body"))
        self.assertIn("actions: read", reviewed_job.group("body"))
        self.assertIn(
            "reviewed-pr: ${{ fromJSON(needs.resolve.outputs.reviewed_pr) }}",
            reviewed_job.group("body"),
        )

        lines = workflow.splitlines()
        run_line = lines.index("        run: |")
        script_lines = []
        for line in lines[run_line + 1 :]:
            if line.startswith("          "):
                script_lines.append(line[10:])
            elif line.strip():
                break
            else:
                script_lines.append("")
        resolve_script = "\n".join(script_lines)

        def resolve(mode, event, tag, reviewed_pr):
            with tempfile.TemporaryDirectory() as directory:
                output_path = Path(directory) / "github-output"
                result = subprocess.run(
                    ["bash", "-c", resolve_script],
                    env={
                        **os.environ,
                        "MODE": mode,
                        "GITHUB_EVENT_NAME": event,
                        "TAG": tag,
                        "REVIEWED_PR": reviewed_pr,
                        "GITHUB_OUTPUT": str(output_path),
                    },
                    capture_output=True,
                    text=True,
                )
                output = output_path.read_text() if output_path.exists() else ""
                return result, output

        result, output = resolve("reviewed-epic", "workflow_dispatch", "v0.4.2", "36")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("tag=v0.4.2\nversion=0.4.2\nmode=reviewed-epic\n", output)
        self.assertIn("reviewed_pr=36\n", output)

        result, _ = resolve("reviewed-epic", "workflow_dispatch", "v0.4.2", "0")
        self.assertNotEqual(result.returncode, 0)

        result, _ = resolve("reviewed-epic", "push", "v0.4.2", "36")
        self.assertNotEqual(result.returncode, 0)

        result, output = resolve("main", "workflow_dispatch", "v0.4.2", "")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("mode=main\n", output)
        self.assertNotIn("reviewed_pr=", output)

        result, _ = resolve("main", "workflow_dispatch", "v0.4.2", "36")
        self.assertNotEqual(result.returncode, 0)

    def test_ordinary_release_still_uses_the_pinned_module_release(self):
        workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text()
        self.assertIn("  push:\n    tags: ['v*']\n", workflow)
        module_job = re.search(
            r"(?ms)^  module-release:\n(?P<body>.*?)(?=^  [a-z0-9-]+:|\Z)",
            workflow,
        )
        self.assertIsNotNone(module_job)
        body = module_job.group("body")
        self.assertIn("if: needs.resolve.outputs.mode == 'main'", body)
        self.assertIn("needs: resolve", body)
        self.assertIn("permissions:\n      contents: write", body)
        self.assertIn(
            "uses: tinyhumansai/.github/.github/workflows/module-release.yml"
            "@4adc1080fb495098e7af1aade82ed7e6e3c69bb7",
            body,
        )
        self.assertIn("tag: ${{ needs.resolve.outputs.tag }}", body)
        self.assertIn("version: ${{ needs.resolve.outputs.version }}", body)
        self.assertIn("module-crate: tinyhosts", body)


if __name__ == "__main__":
    unittest.main()
