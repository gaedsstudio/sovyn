const githubUrl = "https://github.com/gaedsstudio/sovyn";
const discordUrl = "https://discord.gg/bxCnrFFcsg";

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
          <a
            className="button primary"
            href={githubUrl}
            rel="noreferrer"
            target="_blank"
          >
            View Source
          </a>
          <a
            className="button"
            href={discordUrl}
            rel="noreferrer"
            target="_blank"
          >
            Join Discord
          </a>
        </div>
      </div>
    </section>
  );
}
