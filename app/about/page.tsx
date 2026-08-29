import Link from "next/link";

export default function AboutPage() {
  return (
    <section className="rail section">
      <div className="section-heading">
        <p className="eyebrow">About</p>
        <h1 className="headline">SOVYN is built for inspectable local work.</h1>
        <p className="lead">
          SOVYN is an open-source agent runtime and automation ecosystem. It
          combines local models, open-source tools, explicit permissions, and
          reusable workflows to reduce dependence on closed AI services.
        </p>
        <div className="cluster">
          <Link
            className="button primary"
            href="https://github.com/gaedsstudio/sovyn"
          >
            View Source
          </Link>
          <Link className="button" href="https://discord.gg/bxCnrFFcsg">
            Join Discord
          </Link>
        </div>
      </div>
    </section>
  );
}
