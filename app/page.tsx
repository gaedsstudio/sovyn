import Link from "next/link";
import { FeatureGrid, TerminalPanel } from "../components/site";

const values = [
  [
    "MODEL",
    "Users choose the model: local Ollama, open weights, or compatible providers.",
  ],
  [
    "AGENT",
    "The runtime is open source and inspectable instead of hidden behind a hosted box.",
  ],
  [
    "TOOLS",
    "Tool permissions are explicit before filesystem, shell, or network actions run.",
  ],
  [
    "WORKFLOWS",
    "Successful work can become editable automation for later local reuse.",
  ],
] as const;

export default function HomePage() {
  return (
    <>
      <section className="rail hero hero-grid">
        <div>
          <p className="eyebrow">SOVYN</p>
          <h1 className="display">
            Open-source agent infrastructure for real work.
          </h1>
          <p className="lead">
            Your agent. Your models. Your workflows. Your machine.
          </p>
          <div className="cluster">
            <Link className="button primary" href="/hub">
              Explore Hub
            </Link>
            <Link
              className="button"
              href="https://github.com/gaedsstudio/sovyn"
            >
              View on GitHub
            </Link>
          </div>
        </div>
        <TerminalPanel
          title="sovyn"
          lines={[
            "> fix the failing tests",
            "◆ Inspecting project",
            "◆ Running tests",
            "◆ Found failing module",
            "! Permission required",
            "◆ Patch applied",
            "◆ Tests passed",
            "◆ Learned workflow",
          ]}
        />
      </section>
      <section className="rail section">
        <h2 className="section-title">
          Use AI once. Run the work locally again.
        </h2>
        <div className="grid">
          <div className="card">
            <p className="eyebrow">Without reusable automation</p>
            <TerminalPanel
              title="repeat"
              lines={[
                "Run 1 -> AI",
                "Run 2 -> AI",
                "Run 3 -> AI",
                "Run 4 -> AI",
              ]}
            />
          </div>
          <div className="card">
            <p className="eyebrow">With SOVYN</p>
            <TerminalPanel
              title="reuse"
              lines={[
                "Run 1 -> AI-assisted execution",
                "Run 2 -> learned workflow",
                "Run 3 -> learned workflow",
                "Run 4 -> learned workflow",
              ]}
            />
          </div>
        </div>
      </section>
      <FeatureGrid
        title="Nothing important should be hidden from the user."
        items={values}
      />
    </>
  );
}
