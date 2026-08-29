import Link from "next/link";

const docs = [
  ["Installation", "https://github.com/gaedsstudio/sovyn#installation"],
  ["Models", "https://github.com/gaedsstudio/sovyn#configuration"],
  ["Permissions", "/security"],
  ["Workflows", "https://github.com/gaedsstudio/sovyn#workflows"],
  ["Hub", "/hub"],
  ["Registry", "/api/registry/packages"],
  ["Publishing", "/publish"],
  ["GitHub", "https://github.com/gaedsstudio/sovyn"],
] as const;

export default function DocsPage() {
  return (
    <section className="rail section">
      <div className="section-heading">
        <p className="eyebrow">Documentation</p>
        <h1 className="headline">
          Start with the runtime, then inspect the Hub.
        </h1>
        <p className="lead">
          Hosted documentation is intentionally small for v0.1. Source-linked
          docs stay close to the open repository.
        </p>
      </div>
      <div className="grid">
        {docs.map(([label, href]) => (
          <Link className="card feature-card" href={href} key={label}>
            <h2>{label}</h2>
            <p className="muted">{href}</p>
          </Link>
        ))}
      </div>
    </section>
  );
}
