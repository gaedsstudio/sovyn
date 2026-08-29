import Link from "next/link";

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
      <p className="eyebrow">Publish</p>
      <h1 className="headline">Submit source people can inspect.</h1>
      <p className="lead">
        SOVYN Hub v0.1 uses GitHub Issues and Pull Requests for package
        submissions. It does not accept arbitrary code uploads.
      </p>
      <div className="grid">
        {requirements.map((item, index) => (
          <article className="card" key={item}>
            <p className="eyebrow">Requirement {index + 1}</p>
            <h2>{item}</h2>
          </article>
        ))}
      </div>
      <div className="cluster">
        <Link
          className="button primary"
          href="https://github.com/gaedsstudio/sovyn/issues/new/choose"
        >
          Submit a package
        </Link>
        <Link className="button" href="https://github.com/gaedsstudio/sovyn">
          Contribute
        </Link>
      </div>
    </section>
  );
}
