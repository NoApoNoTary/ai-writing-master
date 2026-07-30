import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src/writing_master"
DOMAIN_MODULES = {"handoff", "persona", "personal_context", "research_brief", "voice_presets"}
PLATFORM_PRIMITIVE_ALLOWLIST = {
    "_runfs.py",
    "handoff.py",
    "personal_context.py",
    "research_brief.py",
}


class ArchitectureContractTests(unittest.TestCase):
    @staticmethod
    def _dotted_name(node):
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            prefix = ArchitectureContractTests._dotted_name(node.value)
            return f"{prefix}.{node.attr}" if prefix else node.attr
        return ""

    def test_domain_modules_do_not_import_other_domains_private_symbols(self):
        violations = set()
        for importer in DOMAIN_MODULES:
            path = PACKAGE / f"{importer}.py"
            tree = ast.parse(path.read_text(encoding="utf-8"))
            aliases = {}
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    imported = node.module.removeprefix("writing_master.")
                    if imported in DOMAIN_MODULES and imported != importer:
                        for name in node.names:
                            if name.name.startswith("_"):
                                violations.add(f"{path.name}:{node.lineno} imports {node.module}.{name.name}")
                    if node.module == "writing_master":
                        for name in node.names:
                            if name.name in DOMAIN_MODULES and name.name != importer:
                                aliases[name.asname or name.name] = name.name
                elif isinstance(node, ast.Import):
                    for name in node.names:
                        imported = name.name.removeprefix("writing_master.")
                        if imported in DOMAIN_MODULES and imported != importer:
                            aliases[name.asname or name.name] = imported
            for node in ast.walk(tree):
                if not isinstance(node, ast.Attribute) or not node.attr.startswith("_"):
                    continue
                dotted = self._dotted_name(node)
                owner = dotted.rsplit(".", 1)[0]
                if owner in aliases or any(
                    dotted.startswith(f"writing_master.{domain}._")
                    for domain in DOMAIN_MODULES - {importer}
                ):
                    violations.add(f"{path.name}:{node.lineno} accesses {dotted}")
        self.assertEqual(sorted(violations), [])

    def test_platform_primitives_stay_in_the_existing_linux_low_level_files(self):
        violations = []
        for path in PACKAGE.rglob("*.py"):
            relative = path.relative_to(PACKAGE).as_posix()
            if relative in PLATFORM_PRIMITIVE_ALLOWLIST:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import) and any(name.name == "fcntl" for name in node.names):
                    violations.append(f"{relative}:{node.lineno}: fcntl")
                elif isinstance(node, ast.ImportFrom) and node.module == "fcntl":
                    violations.append(f"{relative}:{node.lineno}: fcntl")
                elif isinstance(node, ast.Constant) and isinstance(node.value, str) and "/proc/self/fd" in node.value:
                    violations.append(f"{relative}:{node.lineno}: /proc/self/fd")
                elif isinstance(node, ast.Call) and any(
                    keyword.arg and keyword.arg.endswith("dir_fd") for keyword in node.keywords
                ):
                    violations.append(f"{relative}:{node.lineno}: dir_fd")
        self.assertEqual(violations, [])

    def test_voice_depends_on_runfs_not_handoff_or_research_internals(self):
        source = (PACKAGE / "voice_presets.py").read_text(encoding="utf-8")
        handoff_source = (PACKAGE / "handoff.py").read_text(encoding="utf-8")
        self.assertIn("from writing_master._runfs import", source)
        self.assertNotIn("writing_master.handoff", source)
        self.assertNotIn("writing_master.research_brief", source)
        self.assertNotIn("_publish_json_once_at", source)
        self.assertIn("from writing_master.voice_presets import VoiceError, validate_snapshot", handoff_source)
        self.assertNotIn("/proc/self/fd", handoff_source)

    def test_codex_host_calls_stay_out_of_runtime_modules(self):
        runtime = "\n".join(path.read_text(encoding="utf-8") for path in PACKAGE.glob("*.py"))
        for token in ("spawn_agent", "fork_turns", "task_name"):
            self.assertNotIn(token, runtime)

    def test_artifact_schema_versions_remain_module_local(self):
        expected = {
            "handoff.py": "SCHEMA_VERSION",
            "personal_context.py": "SCHEMA_VERSION",
            "research_brief.py": "RESEARCH_BRIEF_SCHEMA_VERSION",
            "voice_presets.py": "SCHEMA_VERSION",
        }
        for filename, constant in expected.items():
            tree = ast.parse((PACKAGE / filename).read_text(encoding="utf-8"))
            assignments = {
                target.id: node.value
                for node in tree.body if isinstance(node, ast.Assign)
                for target in node.targets if isinstance(target, ast.Name)
            }
            self.assertIn(constant, assignments, filename)
            self.assertIsInstance(assignments[constant], ast.Constant, filename)
            self.assertIsInstance(assignments[constant].value, int, filename)
            imported = {
                name.name
                for node in tree.body if isinstance(node, ast.ImportFrom)
                for name in node.names
            }
            self.assertNotIn(constant, imported, filename)


if __name__ == "__main__":
    unittest.main()
