import { TerminalPanel } from "../../components/site";

export default function DevelopersPage() {
  return (
    <section className="rail section">
      <div className="section-heading">
        <p className="eyebrow">Developer ecosystem</p>
        <h1 className="headline">
          Packages, manifests, permissions, and future CLI integration.
        </h1>
        <p className="lead">
          SOVYN Hub is the optional network layer. Normal SOVYN usage stays
          local-first and should keep working offline.
        </p>
      </div>
      <div className="grid">
        <div className="card">
          <h2>Future CLI surface</h2>
          <TerminalPanel
            title="planned"
            lines={[
              "sovyn search pytest",
              "sovyn info publisher/package",
              "sovyn install publisher/package",
              "sovyn update",
              "sovyn publish",
            ]}
          />
        </div>
        <div className="card">
          <h2>Verified Developer</h2>
          <p>
            Future profiles may show GitHub identity confirmation, publisher
            history, signed releases, and reviewed package manifests.
          </p>
          <p className="muted">
            No fake identity verification is displayed in v0.1.
          </p>
        </div>
      </div>
    </section>
  );
}
