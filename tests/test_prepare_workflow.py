import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "skills" / "ecom-h3-video" / "scripts" / "prepare_workflow.py"
WORKFLOW = ROOT / "skills" / "ecom-h3-video" / "assets" / "minimax-h3-workflow.json"
SPEC = importlib.util.spec_from_file_location("prepare_workflow", SCRIPT)
preparer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preparer)
ORIGINAL = json.loads(WORKFLOW.read_text(encoding="utf-8"))


def nodes(workflow):
    return {node["id"]: node for node in workflow["nodes"]}


class PrepareWorkflowTests(unittest.TestCase):
    def prepare(self, images=None):
        return preparer.prepare_workflow(
            copy.deepcopy(ORIGINAL),
            prompt="Show the product clearly.",
            duration=10,
            ratio="9:16",
            images=images or [],
        )

    def test_text_input_activates_t2va_without_graph_analysis(self):
        workflow = self.prepare()
        mapped = nodes(workflow)

        self.assertEqual(mapped[307]["mode"], 0)
        self.assertEqual(mapped[333]["mode"], 4)
        self.assertEqual(mapped[363]["mode"], 4)
        self.assertEqual(mapped[307]["widgets_values"][4], "T2VA")
        self.assertEqual(mapped[234]["widgets_values"][0], "Show the product clearly.")
        self.assertEqual(mapped[236]["widgets_values"][0], 10)
        self.assertEqual(mapped[235]["widgets_values"][0], "9:16 (Portrait Widescreen)")
        self.assertNotIn(215, mapped)
        self.assertFalse(any(node["type"] == "MarkdownNote" for node in workflow["nodes"]))

    def test_one_image_activates_single_ref2va(self):
        workflow = self.prepare(["uploaded/product.png"])
        mapped = nodes(workflow)

        self.assertEqual(mapped[307]["mode"], 4)
        self.assertEqual(mapped[333]["mode"], 0)
        self.assertEqual(mapped[363]["mode"], 4)
        self.assertEqual(mapped[333]["widgets_values"][4], "Ref2VA")
        self.assertEqual(mapped[335]["widgets_values"][0], "uploaded/product.png")
        self.assertEqual(workflow["extra"]["dsvideo"]["mode"], "single")

    def test_two_images_activate_multi_ref2va_and_disconnect_third(self):
        workflow = self.prepare(["uploaded/front.png", "uploaded/back.png"])
        mapped = nodes(workflow)

        self.assertEqual(mapped[363]["mode"], 0)
        self.assertEqual(mapped[363]["widgets_values"][4], "Ref2VA")
        self.assertEqual(mapped[362]["widgets_values"][0], "uploaded/front.png")
        self.assertEqual(mapped[364]["widgets_values"][0], "uploaded/back.png")
        self.assertNotIn(365, mapped)
        third = next(item for item in mapped[363]["inputs"] if item["name"] == "ref_images.ref_image_2")
        self.assertIsNone(third["link"])
        self.assertFalse(any(link[0] == 531 for link in workflow["links"]))

    def test_rejects_more_images_than_the_bundled_workflow_supports(self):
        with self.assertRaisesRegex(preparer.WorkflowPrepareError, "at most 3"):
            self.prepare(["1.png", "2.png", "3.png", "4.png"])


if __name__ == "__main__":
    unittest.main()
