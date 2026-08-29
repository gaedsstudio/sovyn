import { TerminalPanel } from "../../components/site";

export default function SecurityPage() {
  return (
    <section className="rail section">
      <p className="eyebrow">Security model</p>
      <h1 className="headline">Verified is review, not a guarantee.</h1>
      <p className="lead">
        Users should evaluate source repositories, publisher status, license,
        manifest, permissions, network access, and release integrity before
        running packages.
      </p>
      <div className="grid">
        <div className="card">
          <h2>Review chain</h2>
          <TerminalPanel
            title="registry"
            lines={[
              "Source repository",
              "↓",
              "Manifest",
              "↓",
              "Permission declaration",
              "↓",
              "Registry validation",
              "↓",
              "User review",
              "↓",
              "Runtime permission enforcement",
            ]}
          />
        </div>
        <div className="card">
          <h2>Verified means</h2>
          <p>
            Publisher identity reviewed, source repository verified, release
            integrity checked, manifest inspected, and permission declarations
            reviewed.
          </p>
          <p className="muted">
            It does not mean guaranteed safe, malware-proof, or officially
            endorsed forever.
          </p>
        </div>
      </div>
    </section>
  );
}
