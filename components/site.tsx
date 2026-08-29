import type { PackageRecord } from "../lib/registry/types";

type FeatureItem = readonly [label: string, body: string];

export function TerminalPanel({
  title,
  lines,
}: Readonly<{ title: string; lines: readonly string[] }>) {
  return (
    <div className="terminal">
      <div className="terminal-bar">
        <span>{title}</span>
        <span>local</span>
      </div>
      <pre>{lines.join("\n")}</pre>
    </div>
  );
}

export function FeatureGrid({
  title,
  items,
}: Readonly<{ title: string; items: readonly FeatureItem[] }>) {
  return (
    <section className="rail section">
      <div className="section-heading">
        <h2 className="section-title">{title}</h2>
      </div>
      <div className="grid">
        {items.map(([label, body], index) => (
          <article className="card feature-card" key={label}>
            <span aria-hidden="true" className={getIconClassName(index)}>
              {label.slice(0, 2)}
            </span>
            <p className="eyebrow">{label}</p>
            <p>{body}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

export function PackageCard({ item }: Readonly<{ item: PackageRecord }>) {
  return (
    <article className="card package-card">
      <div className="cluster">
        <div className="cluster">
          <span
            className={item.status === "verified" ? "badge verified" : "badge"}
          >
            {item.status === "verified" ? "Verified" : "Community"}
          </span>
          <span className="badge">{item.license}</span>
        </div>
        <div className="cluster">
          <a className="button" href={item.source.repository}>
            Source
          </a>
          <a className="button primary" href={`/package/${item.slug}`}>
            Details
          </a>
        </div>
      </div>
      <h3>{item.name}</h3>
      <p>{item.description}</p>
      <div className="package-meta">
        <span>Publisher: {item.publisher}</span>
        <span>Permissions: {item.permissions.summary.join(" / ")}</span>
      </div>
    </article>
  );
}

export function PermissionTable({ item }: Readonly<{ item: PackageRecord }>) {
  const network = item.permissions.network
    ? item.permissions.network.join(", ")
    : "None";
  return (
    <table className="table">
      <tbody>
        <tr>
          <th scope="row">Filesystem read</th>
          <td>{item.permissions.filesystem.read.join(", ")}</td>
        </tr>
        <tr>
          <th scope="row">Filesystem write</th>
          <td>
            {item.permissions.filesystem.write.length > 0
              ? item.permissions.filesystem.write.join(", ")
              : "None"}
          </td>
        </tr>
        <tr>
          <th scope="row">Shell</th>
          <td>
            {item.permissions.shell.length > 0
              ? item.permissions.shell.join(", ")
              : "None"}
          </td>
        </tr>
        <tr>
          <th scope="row">Network</th>
          <td>{network}</td>
        </tr>
      </tbody>
    </table>
  );
}

function getIconClassName(index: number): string {
  switch (index % 4) {
    case 1:
      return "icon-well blue";
    case 2:
      return "icon-well green";
    case 3:
      return "icon-well violet";
    default:
      return "icon-well";
  }
}
