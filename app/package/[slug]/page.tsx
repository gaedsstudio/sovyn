import { notFound } from "next/navigation";
import { CopyButton } from "../../../components/copy-button";
import { PermissionTable } from "../../../components/site";
import {
  getPackage,
  getPublisher,
  listPackages,
} from "../../../lib/registry/registry";

type PackagePageProps = {
  readonly params: Promise<{
    readonly slug: string;
  }>;
};

export function generateStaticParams() {
  return listPackages().map((item) => ({ slug: item.slug }));
}

export default async function PackagePage({ params }: PackagePageProps) {
  const { slug } = await params;
  const item = getPackage(slug);
  if (item === null) {
    notFound();
  }
  const publisher = getPublisher(item.publisher);
  return (
    <section className="rail section">
      <div className="section-heading">
        <p className="eyebrow">
          {item.status === "verified" ? "Verified" : "Community"}
        </p>
        <h1 className="headline">{item.name}</h1>
        <p className="lead">{item.description}</p>
      </div>
      <div className="grid">
        <div className="card">
          <h2>Source</h2>
          <table className="table">
            <tbody>
              <tr>
                <th scope="row">Publisher</th>
                <td>{publisher?.displayName ?? item.publisher}</td>
              </tr>
              <tr>
                <th scope="row">Version</th>
                <td>{item.version}</td>
              </tr>
              <tr>
                <th scope="row">License</th>
                <td>{item.license}</td>
              </tr>
              <tr>
                <th scope="row">Repository</th>
                <td>
                  <a href={item.source.repository}>{item.source.repository}</a>
                </td>
              </tr>
              <tr>
                <th scope="row">Release</th>
                <td>{item.source.releaseTag ?? "Not declared"}</td>
              </tr>
              <tr>
                <th scope="row">Commit</th>
                <td>{item.source.commit ?? "Not declared"}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div className="card">
          <h2>Install</h2>
          {item.installCommand === null ? (
            <p>Hub install command is not available for this package yet.</p>
          ) : (
            <>
              <TerminalPanelLike value={item.installCommand} />
              <CopyButton value={item.installCommand} />
            </>
          )}
        </div>
      </div>
      <div className="grid">
        <div className="card">
          <h2>Permissions</h2>
          <PermissionTable item={item} />
        </div>
        <div className="card">
          <h2>Security information</h2>
          <ul>
            {item.securityNotes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </div>
      </div>
      <article className="card">
        <h2>README</h2>
        <p>{item.readme}</p>
      </article>
    </section>
  );
}

function TerminalPanelLike({ value }: Readonly<{ value: string }>) {
  return (
    <div className="terminal">
      <div className="terminal-bar">
        <span>command</span>
        <span>copy only</span>
      </div>
      <pre>{value}</pre>
    </div>
  );
}
