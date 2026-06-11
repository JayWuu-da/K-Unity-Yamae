"""Unity verifier - runs compile/import, tests, and custom probes via batchmode."""

import re
import subprocess
from pathlib import Path


class UnityVerifier:
    def __init__(self, project_path: Path, config: dict):
        self.project_path = project_path
        self.config = config
        self.unity_config = config.get("unity", {})
        self.verify_config = config.get("verification", {})
        self.reports_dir = project_path / ".unity-harness" / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        timeouts = self.config.get("verification", {}).get("timeouts", {})
        self.timeout_compile = timeouts.get("compile", 300)
        self.timeout_tests = timeouts.get("tests", 600)
        self.timeout_build = timeouts.get("build", 1800)

    def verify(
        self,
        compile_check: bool = True,
        editmode_tests: bool = False,
        playmode_tests: bool = False,
        build_target: str | None = None,
        custom_method: str | None = None,
    ) -> list[dict]:
        """Run configured Unity verification commands."""
        results = []
        unity_exe = self._find_unity_executable()

        if compile_check:
            result = self._run_compile_check(unity_exe)
            result["tier"] = "1"
            results.append(result)

        if editmode_tests:
            result = self._run_editmode_tests(unity_exe)
            result["tier"] = "2"
            results.append(result)

        if playmode_tests:
            result = self._run_playmode_tests(unity_exe)
            result["tier"] = "3"
            results.append(result)

        if custom_method or self.unity_config.get("custom_validation_method"):
            method = custom_method or self.unity_config["custom_validation_method"]
            result = self._run_custom_method(unity_exe, method)
            result["tier"] = "4"
            results.append(result)

        if build_target:
            result = self._run_build(unity_exe, build_target)
            result["tier"] = "5"
            results.append(result)

        return results

    def plan(
        self,
        compile_check: bool = True,
        editmode_tests: bool = False,
        playmode_tests: bool = False,
        build_target: str | None = None,
        custom_method: str | None = None,
    ) -> list[dict]:
        unity_exe = self._planned_unity_executable()
        project_path = self._unity_project_path()
        results = []
        if compile_check:
            results.append(
                {
                    "name": "compile/import",
                    "tier": "1",
                    "status": "planned",
                    "passed": False,
                    "command": [
                        unity_exe,
                        "-batchmode",
                        "-quit",
                        "-projectPath",
                        project_path,
                        "-logFile",
                        str(self.reports_dir / "compile.log"),
                    ],
                }
            )
        if editmode_tests:
            results.append(
                self._planned_test_command(unity_exe, project_path, "EditMode", "editmode")
            )
        if playmode_tests:
            results.append(
                self._planned_test_command(unity_exe, project_path, "PlayMode", "playmode")
            )
        if custom_method or self.unity_config.get("custom_validation_method"):
            method = custom_method or self.unity_config["custom_validation_method"]
            results.append(
                {
                    "name": "custom_method",
                    "tier": "4",
                    "status": "planned",
                    "passed": False,
                    "command": [
                        unity_exe,
                        "-batchmode",
                        "-quit",
                        "-projectPath",
                        project_path,
                        "-executeMethod",
                        method,
                        "-logFile",
                        str(self.reports_dir / "custom.log"),
                    ],
                }
            )
        if build_target:
            results.append(
                {
                    "name": f"build_{build_target}",
                    "tier": "5",
                    "status": "planned",
                    "passed": False,
                    "command": [
                        unity_exe,
                        "-batchmode",
                        "-quit",
                        "-projectPath",
                        project_path,
                        "-buildTarget",
                        build_target,
                        "-logFile",
                        str(self.reports_dir / f"build_{build_target}.log"),
                    ],
                }
            )
        return results

    def _planned_unity_executable(self) -> str:
        configured = self.unity_config.get("executable")
        if configured and configured != "auto":
            return str(configured)
        return self._find_unity_executable() or "Unity"

    def _planned_test_command(
        self,
        unity_exe: str,
        project_path: str,
        test_platform: str,
        basename: str,
    ) -> dict:
        results_dir = self.project_path / self.unity_config.get(
            "test_results_dir", ".unity-harness/reports/test-results"
        )
        return {
            "name": f"{basename}_tests",
            "tier": "2" if test_platform == "EditMode" else "3",
            "status": "planned",
            "passed": False,
            "command": [
                unity_exe,
                "-batchmode",
                "-runTests",
                "-projectPath",
                project_path,
                "-testPlatform",
                test_platform,
                "-testResults",
                str(results_dir / f"{basename}.xml"),
                "-logFile",
                str(self.reports_dir / f"{basename}.log"),
            ],
        }

    def _run_compile_check(self, unity_exe: str | None) -> dict:
        if not unity_exe:
            return {
                "name": "compile/import",
                "status": "skipped",
                "passed": False,
                "details": "Unity executable not found",
                "log_path": "",
            }

        log_path = self.reports_dir / "compile.log"
        project_path = self._unity_project_path()

        cmd = [
            unity_exe,
            "-batchmode",
            "-quit",
            "-projectPath",
            project_path,
            "-logFile",
            str(log_path),
        ]

        try:
            result = self._run_unity_command(cmd, self.timeout_compile)
            log_content = (
                log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
            )
            parsed = self._parse_unity_log(log_content)

            if result.returncode == 0 and not parsed["errors"]:
                return {
                    "name": "compile/import",
                    "status": "passed",
                    "passed": True,
                    "details": "Compile/import succeeded",
                    "log_path": str(log_path),
                }
            else:
                error_summary = "; ".join(parsed["errors"][:3])
                return {
                    "name": "compile/import",
                    "status": "failed",
                    "passed": False,
                    "details": f"Errors: {error_summary}",
                    "log_path": str(log_path),
                }
        except subprocess.TimeoutExpired:
            return {
                "name": "compile/import",
                "status": "timeout",
                "passed": False,
                "details": "Unity batchmode timed out after 300s",
                "log_path": str(log_path),
            }
        except FileNotFoundError:
            return {
                "name": "compile/import",
                "status": "skipped",
                "passed": False,
                "details": "Unity executable not found",
                "log_path": "",
            }

    def _run_editmode_tests(self, unity_exe: str | None) -> dict:
        if not unity_exe:
            return {
                "name": "editmode_tests",
                "status": "skipped",
                "passed": False,
                "details": "Unity executable not found",
                "log_path": "",
            }

        results_dir = self.unity_config.get(
            "test_results_dir", ".unity-harness/reports/test-results"
        )
        results_path = self.project_path / results_dir
        results_path.mkdir(parents=True, exist_ok=True)
        test_results = results_path / "editmode.xml"
        log_path = self.reports_dir / "editmode.log"
        project_path = self._unity_project_path()

        cmd = [
            unity_exe,
            "-batchmode",
            "-runTests",
            "-projectPath",
            project_path,
            "-testPlatform",
            "EditMode",
            "-testResults",
            str(test_results),
            "-logFile",
            str(log_path),
        ]

        try:
            self._run_unity_command(cmd, self.timeout_tests)
            if test_results.exists():
                xml_content = test_results.read_text(encoding="utf-8")
                passed = (
                    'result="passed"' in xml_content.lower() or 'result="Passed"' in xml_content
                )
                failed_count = xml_content.count('result="Failed"') + xml_content.count(
                    'result="failed"'
                )
                return {
                    "name": "editmode_tests",
                    "status": "passed" if passed else "failed",
                    "passed": passed,
                    "details": f"Failed: {failed_count}",
                    "log_path": str(log_path),
                    "xml_path": str(test_results),
                }
            return {
                "name": "editmode_tests",
                "status": "no_results",
                "passed": False,
                "details": "No test results generated",
                "log_path": str(log_path),
            }
        except subprocess.TimeoutExpired:
            return {
                "name": "editmode_tests",
                "status": "timeout",
                "passed": False,
                "details": "EditMode tests timed out after 600s",
                "log_path": str(log_path),
            }

    def _run_playmode_tests(self, unity_exe: str | None) -> dict:
        if not unity_exe:
            return {
                "name": "playmode_tests",
                "status": "skipped",
                "passed": False,
                "details": "Unity executable not found",
                "log_path": "",
            }

        results_dir = self.unity_config.get(
            "test_results_dir", ".unity-harness/reports/test-results"
        )
        results_path = self.project_path / results_dir
        results_path.mkdir(parents=True, exist_ok=True)
        test_results = results_path / "playmode.xml"
        log_path = self.reports_dir / "playmode.log"
        project_path = self._unity_project_path()

        cmd = [
            unity_exe,
            "-batchmode",
            "-runTests",
            "-projectPath",
            project_path,
            "-testPlatform",
            "PlayMode",
            "-testResults",
            str(test_results),
            "-logFile",
            str(log_path),
        ]

        try:
            self._run_unity_command(cmd, self.timeout_tests)
            if test_results.exists():
                xml_content = test_results.read_text(encoding="utf-8")
                passed = (
                    'result="passed"' in xml_content.lower() or 'result="Passed"' in xml_content
                )
                failed_count = xml_content.count('result="Failed"') + xml_content.count(
                    'result="failed"'
                )
                return {
                    "name": "playmode_tests",
                    "status": "passed" if passed else "failed",
                    "passed": passed,
                    "details": f"Failed: {failed_count}",
                    "log_path": str(log_path),
                    "xml_path": str(test_results),
                }
            return {
                "name": "playmode_tests",
                "status": "no_results",
                "passed": False,
                "details": "No test results generated",
                "log_path": str(log_path),
            }
        except subprocess.TimeoutExpired:
            return {
                "name": "playmode_tests",
                "status": "timeout",
                "passed": False,
                "details": "PlayMode tests timed out after 600s",
                "log_path": str(log_path),
            }

    def _run_build(self, unity_exe: str | None, target: str) -> dict:
        if not unity_exe:
            return {
                "name": f"build_{target}",
                "status": "skipped",
                "passed": False,
                "details": "Unity executable not found",
                "log_path": "",
            }

        log_path = self.reports_dir / f"build_{target}.log"
        project_path = self._unity_project_path()
        cmd = [
            unity_exe,
            "-batchmode",
            "-quit",
            "-projectPath",
            project_path,
            "-buildTarget",
            target,
            "-executeMethod",
            "UnityEditor.BuildPipeline.BuildPlayer",
            "-logFile",
            str(log_path),
        ]

        try:
            result = self._run_unity_command(cmd, self.timeout_build)
            log_content = (
                log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
            )
            if "Build succeeded" in log_content or result.returncode == 0:
                return {
                    "name": f"build_{target}",
                    "status": "passed",
                    "passed": True,
                    "details": f"Build to {target} succeeded",
                    "log_path": str(log_path),
                }
            return {
                "name": f"build_{target}",
                "status": "failed",
                "passed": False,
                "details": f"Build to {target} failed",
                "log_path": str(log_path),
            }
        except subprocess.TimeoutExpired:
            return {
                "name": f"build_{target}",
                "status": "timeout",
                "passed": False,
                "details": "Build timed out after 1800s",
                "log_path": str(log_path),
            }

    def _run_custom_method(self, unity_exe: str | None, method: str) -> dict:
        if not unity_exe:
            return {
                "name": f"custom_{method.split('.')[-1]}",
                "status": "skipped",
                "passed": False,
                "details": "Unity executable not found",
                "log_path": "",
            }

        log_path = self.reports_dir / "custom_probe.log"
        project_path = self._unity_project_path()

        cmd = [
            unity_exe,
            "-batchmode",
            "-quit",
            "-projectPath",
            project_path,
            "-executeMethod",
            method,
            "-logFile",
            str(log_path),
        ]

        try:
            result = self._run_unity_command(cmd, self.timeout_compile)
            log_content = (
                log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
            )
            if "HARNESS_CHECKS_COMPLETE" in log_content or result.returncode == 0:
                return {
                    "name": f"custom_{method.split('.')[-1]}",
                    "status": "passed",
                    "passed": True,
                    "details": f"Custom method {method} succeeded",
                    "log_path": str(log_path),
                }
            return {
                "name": f"custom_{method.split('.')[-1]}",
                "status": "failed",
                "passed": False,
                "details": f"Custom method {method} failed{self._process_output_summary(result)}",
                "log_path": str(log_path),
            }
        except subprocess.TimeoutExpired:
            return {
                "name": f"custom_{method.split('.')[-1]}",
                "status": "timeout",
                "passed": False,
                "details": "Custom method timed out",
                "log_path": str(log_path),
            }

    def _parse_unity_log(self, log_content: str) -> dict:
        errors = []
        warnings = []
        for line in log_content.splitlines():
            if re.search(r"Compiler error|CS\d{4}", line):
                errors.append(line.strip()[:200])
            elif "Exception" in line and ("import" in line.lower() or "compile" in line.lower()):
                errors.append(line.strip()[:200])
            elif "MissingReferenceException" in line or "NullReferenceException" in line:
                errors.append(line.strip()[:200])
            elif "warning CS" in line:
                warnings.append(line.strip()[:200])
        return {"errors": errors, "warnings": warnings}

    def _run_unity_command(self, cmd: list[str], timeout: int) -> subprocess.CompletedProcess:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )

    def _unity_project_path(self) -> str:
        configured = self.unity_config.get("project_path")
        if not configured or configured == ".":
            return str(self.project_path)
        return str(configured)

    def _process_output_summary(self, result: subprocess.CompletedProcess) -> str:
        parts = []
        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()
        if stdout:
            parts.append(f"stdout: {stdout[:200]}")
        if stderr:
            parts.append(f"stderr: {stderr[:200]}")
        return " (" + "; ".join(parts) + ")" if parts else ""

    def _find_unity_executable(self) -> str | None:
        exe = self.unity_config.get("executable", "auto")
        if exe != "auto":
            return exe
        import platform

        system = platform.system()
        if system == "Windows":
            paths = [
                r"C:\Program Files\Unity\Hub\Editor\*\Editor\Unity.exe",
                r"C:\Program Files\Unity\Hub\Editor\*\Editor\Data\PlaybackEngines\*\Unity.exe",
            ]
        elif system == "Darwin":
            paths = [
                "/Applications/Unity/Hub/Editor/*/Unity.app/Contents/MacOS/Unity",
            ]
        else:
            paths = [
                "/opt/unity/Editor/Unity",
                "/usr/bin/unity",
            ]
        import glob

        for pattern in paths:
            matches = glob.glob(pattern)
            if matches:
                return sorted(matches)[-1]
        return None
