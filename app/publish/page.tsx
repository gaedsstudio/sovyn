const githubUrl = "https://github.com/gaedsstudio/sovyn";
const githubIssueChooserUrl =
  "https://github.com/gaedsstudio/sovyn/issues/new/choose";

const requirements = [
  "Open-source repository",
  "Valid license",
  "SOVYN package manifest",
  "Declared permissions",
  "Public source",
  "Submission via GitHub",
] as const;

export default function PublishPage() {
  return (
    <section className="rail section">
      <div className="section-heading">
        <p className="eyebrow">Publish</p>
        <h1 className="headline">Submit source people can inspect.</h1>
        <p className="lead">
          SOVYN Hub v0.1 uses GitHub Issues and Pull Requests for package
          submissions. It does not accept arbitrary code uploads.
        </p>
      </div>
      <div className="grid">
        {requirements.map((item, index) => (
          <article className="card feature-card" key={item}>
            <p className="eyebrow">Requirement {index + 1}</p>
            <h2>{item}</h2>
          </article>
        ))}
      </div>
      <div className="cluster">
        <a
          className="button primary"
          href={githubIssueChooserUrl}
          rel="noreferrer"
          target="_blank"
        >
          Submit a package
        </a>
        <a className="button" href={githubUrl} rel="noreferrer" target="_blank">
          Contribute
        </a>
      </div>
    </section>
  );
}
