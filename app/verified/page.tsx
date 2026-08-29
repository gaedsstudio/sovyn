import { PackageCard } from "../../components/site";
import { listVerifiedPackages } from "../../lib/registry/registry";

export default function VerifiedPage() {
  const packages = listVerifiedPackages();
  return (
    <section className="rail section">
      <p className="eyebrow">◈ Verified Publisher</p>
      <h1 className="headline">Reviewed source, not guaranteed safety.</h1>
      <p className="lead">
        Verified means publisher identity, source repository, release integrity,
        package manifest, and permission declarations have been reviewed. It
        does not mean malware-proof, risk-free, or permanently endorsed.
      </p>
      <div className="grid">
        {packages.map((item) => (
          <PackageCard item={item} key={item.slug} />
        ))}
      </div>
      {packages.length === 0 ? (
        <div className="card">
          <h2>Verified packages are reviewed before appearing here.</h2>
          <p>
            Until review is complete, inspect community packages directly
            through their public source.
          </p>
        </div>
      ) : null}
    </section>
  );
}
