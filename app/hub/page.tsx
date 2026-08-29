import Link from "next/link";
import { PackageCard } from "../../components/site";
import { searchPackages } from "../../lib/registry/search";

type HubPageProps = {
  readonly searchParams?: Promise<{
    readonly q?: string;
  }>;
};

export default async function HubPage({ searchParams }: HubPageProps) {
  const params = await searchParams;
  const query = params?.q ?? "";
  const packages = searchPackages(query);
  return (
    <section className="rail section">
      <div className="section-heading">
        <p className="eyebrow">SOVYN Hub</p>
        <h1 className="headline">
          Inspectable packages for local-first automation.
        </h1>
        <p className="lead">
          Search first-party and community SOVYN packages by name, publisher,
          tags, and declared purpose.
        </p>
      </div>
      <form className="search" action="/hub">
        <label htmlFor="hub-search">Search packages</label>
        <input
          id="hub-search"
          name="q"
          placeholder="Search packages (e.g. pytest, workflow, ollama)..."
          defaultValue={query}
        />
        <button className="button dark" type="submit">
          Search Hub
        </button>
      </form>
      <div className="grid">
        {packages.map((item) => (
          <PackageCard item={item} key={item.slug} />
        ))}
      </div>
      {packages.length === 0 ? (
        <div className="card">
          <h2>No packages matched.</h2>
          <p>
            Try a different term, or publish an open-source workflow through
            GitHub.
          </p>
          <Link className="button" href="/publish">
            Publishing guide
          </Link>
        </div>
      ) : null}
      <div className="grid compact">
        <div className="card feature-card">
          <h2>Verified</h2>
          <p>
            Reviewed publisher, source, release integrity, manifest, and
            permission declarations.
          </p>
          <Link className="button" href="/verified">
            View verified
          </Link>
        </div>
        <div className="card feature-card">
          <h2>Community</h2>
          <p>
            No community packages yet. SOVYN Hub is new, and submissions start
            through public GitHub work.
          </p>
          <Link className="button" href="/community">
            View community
          </Link>
        </div>
        <div className="card feature-card">
          <h2>Publish</h2>
          <p>
            Bring a public repository, license, manifest, and explicit
            permissions.
          </p>
          <Link className="button" href="/publish">
            Submit a package
          </Link>
        </div>
      </div>
    </section>
  );
}
