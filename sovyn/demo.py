from sovyn.ui import DiamondState, Renderer


def run_demo(renderer: Renderer) -> None:
    renderer.line(DiamondState.WAITING, "Inspecting workspace...")
    renderer.line(DiamondState.COMPLETED, "63 source files found")
    renderer.line(DiamondState.WAITING, "Checking Git...")
    renderer.line(DiamondState.COMPLETED, "Git repository detected")
    renderer.line(DiamondState.WAITING, "Running tests...")
    renderer.line(DiamondState.COMPLETED, "13 passed")
    renderer.line(DiamondState.ATTENTION, "This task could be saved as a workflow. Create workflow? [Y/n]")
