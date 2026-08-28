from sovyn.ui import DiamondState, Renderer


def run_demo(renderer: Renderer) -> None:
    renderer.line(DiamondState.WAITING, "Inspecting workspace...")
    renderer.line(DiamondState.COMPLETED, "184 files indexed")
    renderer.line(DiamondState.WAITING, "Checking project structure...")
    renderer.line(DiamondState.COMPLETED, "Python project detected")
    renderer.line(DiamondState.WAITING, "Running tests...")
    renderer.line(DiamondState.COMPLETED, "Tests completed")
    renderer.line(DiamondState.WAITING, "Investigating...")
    renderer.line(DiamondState.COMPLETED, "Suggested patch ready")
    renderer.line(DiamondState.ATTENTION, "Apply changes? [Y/n]")
