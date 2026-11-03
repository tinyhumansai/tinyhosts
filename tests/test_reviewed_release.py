"""Contract tests for the TinyHosts release route: releases come from main only."""

import os
import re
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


# The TinyBus SDK range and the vendored checkout move together: bump both here
# when vendor/tinybus moves. 6ce06bc is TinyBus v0.3.6, the range's lower bound.
TINYBUS_SDK_RANGE = ">=0.3.6, <0.4"
TINYBUS_VENDOR_COMMIT = "6ce06bc674e4f4d718aa51e643ef62c1f372e270"


class ReviewedReleaseContractTests(unittest.TestCase):
    def test_release_manifest_and_tinybus_sdk_are_pinned_together(self):
        manifest = tomllib.loads((ROOT / "Cargo.toml").read_text())
        bus_manifest = tomllib.loads((ROOT / "crates" / "tinyhosts-bus" / "Cargo.toml").read_text())
        version = manifest["package"]["version"]
        self.assertEqual(bus_manifest["package"]["version"], version)
        self.assertEqual(manifest["dependencies"]["tinyhosts-bus"]["version"], version)
        self.assertEqual(manifest["dependencies"]["tinybus"]["version"], TINYBUS_SDK_RANGE)
        self.assertEqual(manifest["dependencies"]["tinybus-module"]["version"], TINYBUS_SDK_RANGE)
        self.assertEqual(
            subprocess.check_output(
                ["git", "-C", str(ROOT), "rev-parse", "HEAD:vendor/tinybus"], text=True
            ).strip(),
            TINYBUS_VENDOR_COMMIT,
        )

    def test_no_release_route_besides_main(self):
        workflows = ROOT / ".github" / "workflows"
        self.assertFalse((workflows / "release-reviewed-epic.yml").exists())
        for path in (ROOT / ".github").rglob("*.yml"):
            text = path.read_text()
            self.assertNotIn("module-reviewed-epic-release", text, path)
            self.assertNotIn("6ed83b04aab2d8977ec62e966cb914531e534fa4", text, path)

        workflow = (workflows / "release.yml").read_text()
        self.assertIn("  push:\n    tags: ['v*']\n", workflow)
        dispatch = re.search(r"(?ms)^  workflow_dispatch:\n(?P<body>.*?)(?=^  push:)", workflow)
        self.assertIsNotNone(dispatch)
        self.assertEqual(
            re.findall(r"^      ([a-z_-]+):$", dispatch.group("body"), re.MULTILINE), ["tag"]
        )
        self.assertNotIn("release_mode", workflow)
        self.assertNotIn("reviewed_pr", workflow)

        jobs = re.findall(r"^  ([a-z0-9-]+):$", workflow.split("\njobs:\n", 1)[1], re.MULTILINE)
        self.assertEqual(jobs, ["resolve", "module-release"])
        body = workflow.split("  module-release:\n", 1)[1]
        self.assertNotIn("    if:", body)
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

    def test_resolver_refuses_a_dispatch_from_any_branch_but_main(self):
        workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text()
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

        def resolve(event, ref, tag):
            with tempfile.TemporaryDirectory() as directory:
                output_path = Path(directory) / "github-output"
                result = subprocess.run(
                    ["bash", "-c", resolve_script],
                    env={
                        **os.environ,
                        "GITHUB_EVENT_NAME": event,
                        "GITHUB_REF": ref,
                        "TAG": tag,
                        "GITHUB_OUTPUT": str(output_path),
                    },
                    capture_output=True,
                    text=True,
                )
                output = output_path.read_text() if output_path.exists() else ""
                return result, output

        result, output = resolve("push", "refs/tags/v0.4.5", "v0.4.5")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(output, "tag=v0.4.5\nversion=0.4.5\n")

        result, output = resolve("workflow_dispatch", "refs/heads/main", "v0.4.5")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(output, "tag=v0.4.5\nversion=0.4.5\n")

        for ref in ["refs/heads/epic/8369-security-migration", "refs/heads/epic/8056-modules-wiring", "refs/tags/v0.4.5"]:
            result, output = resolve("workflow_dispatch", ref, "v0.4.5")
            self.assertNotEqual(result.returncode, 0, ref)
            self.assertIn("release must be dispatched from main", result.stderr)
            self.assertEqual(output, "")

        result, _ = resolve("push", "refs/tags/release-1", "release-1")
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
