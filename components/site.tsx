import type { PackageRecord } from "../lib/registry/types";

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
}: Readonly<{ title: string; items: readonly (readonly [string, string])[] }>) {
  return (
    <section className="rail section">
      <h2 className="section-title">{title}</h2>
      <div className="grid">
        {items.map(([label, body]) => (
          <article className="card" key={label}>
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
    <article className="card">
      <div className="cluster">
        <span
          className={item.status === "verified" ? "badge verified" : "badge"}
        >
          {item.status === "verified" ? "◈ Verified" : "◇ Community"}
        </span>
        <span className="badge">{item.license}</span>
      </div>
      <h3>{item.name}</h3>
      <p>{item.description}</p>
      <p className="muted">Publisher: {item.publisher}</p>
      <p className="muted">
        Permissions: {item.permissions.summary.join(" · ")}
      </p>
      <div className="cluster">
        <a className="button" href={`/package/${item.slug}`}>
          Details
        </a>
        <a className="button" href={item.source.repository}>
          View Source
        </a>
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
