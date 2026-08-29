import Link from "next/link";
import { listPackages } from "../../lib/registry/registry";

export default function CommunityPage() {
  const communityPackages = listPackages().filter(
    (item) => item.status === "community",
  );
  return (
    <section className="rail section">
      <p className="eyebrow">Community registry</p>
      <h1 className="headline">
        Open-source packages should remain inspectable.
      </h1>
      <p className="lead">
        Community packages require public source, an open-source license,
        package metadata, and an explicit permission manifest. v0.1 submissions
        happen through GitHub Issues or Pull Requests, not arbitrary code
        upload.
      </p>
      {communityPackages.length === 0 ? (
        <div className="card">
          <h2>No community packages yet.</h2>
          <p>
            SOVYN Hub is new. Publish an open-source workflow or tool and become
            one of the first contributors.
          </p>
          <div className="cluster">
            <Link className="button primary" href="/publish">
              Publish the first package
            </Link>
            <Link className="button" href="https://discord.gg/bxCnrFFcsg">
              Discord
            </Link>
          </div>
        </div>
      ) : null}
    </section>
  );
}
