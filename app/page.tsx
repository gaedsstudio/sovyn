import Link from "next/link";
import { FeatureGrid, PackageCard } from "../components/site";
import { listPackages } from "../lib/registry/registry";

const values = [
  [
    "Model Choice",
    "Users choose the model: local Ollama, open weights, or compatible providers.",
  ],
  [
    "Inspectable Agent",
    "The runtime is open source and inspectable instead of hidden behind a hosted box.",
  ],
  [
    "Explicit Tools",
    "Tool permissions are explicit before filesystem, shell, or network actions run.",
  ],
  [
    "Workflows",
    "Successful work can become editable automation for later local reuse.",
  ],
] as const;

const faqs = [
  [
    "How does SOVYN differ from cloud-hosted agents?",
    "SOVYN executes locally on your hardware. You keep oversight and granular approval over filesystem, shell, and network actions.",
  ],
  [
    "Can I use local Ollama models?",
    "Yes. SOVYN supports local Ollama runtimes and standard OpenAI-compatible endpoints so you can choose the model layer.",
  ],
  [
    "How are learned workflows reused?",
    "Successful AI-assisted work can be captured as editable local automation, reducing repeated API calls for repeatable tasks.",
  ],
] as const;

export default function HomePage() {
  const featuredPackage = listPackages()[0];
  return (
    <>
      <section className="rail hero">
        <h1 className="display">Open-source agent runtime for real work.</h1>
        <p className="lead">
          Your agent. Your models. Your workflows. Your machine. Inspectable
          local execution with complete freedom.
        </p>
        <div className="cluster">
          <Link className="button primary" href="/hub">
            Explore Hub
          </Link>
          <Link className="button" href="https://github.com/gaedsstudio/sovyn">
            View on GitHub
          </Link>
        </div>
      </section>
      <FeatureGrid title="Nothing hidden from the user" items={values} />
      <section className="rail section" id="hub">
        <div className="section-heading">
          <h2 className="section-title">Inspectable Package Hub</h2>
          <p className="lead">
            Discover and install verified packages for local-first automation.
          </p>
        </div>
        <form className="search" action="/hub">
          <label htmlFor="home-hub-search">Search packages</label>
          <input
            id="home-hub-search"
            name="q"
            placeholder="Search packages (e.g. pytest, workflow, ollama)..."
          />
          <button className="button dark" type="submit">
            Search Hub
          </button>
        </form>
        {featuredPackage ? <PackageCard item={featuredPackage} /> : null}
        <div className="grid compact">
          <article className="card feature-card">
            <h3>Verified Directory</h3>
            <p>Curated and reviewed publishers and integrity manifests.</p>
            <Link className="button" href="/verified">
              View verified
            </Link>
          </article>
          <article className="card feature-card">
            <h3>Community Packages</h3>
            <p>Discover community contributions directly from GitHub.</p>
            <Link className="button" href="/community">
              Browse community
            </Link>
          </article>
          <article className="card feature-card">
            <h3>Publish Work</h3>
            <p>Register your custom runtime tools and manifests.</p>
            <Link className="button" href="/publish">
              Submit package
            </Link>
          </article>
        </div>
      </section>
      <section className="rail section">
        <div className="section-heading">
          <h2 className="section-title">Frequently Asked Questions</h2>
        </div>
        <div className="faq-list">
          {faqs.map(([question, answer]) => (
            <details key={question}>
              <summary>
                <span>{question}</span>
                <span className="faq-marker" aria-hidden="true">
                  +
                </span>
              </summary>
              <p>{answer}</p>
            </details>
          ))}
        </div>
      </section>
      <section className="band band-dark">
        <div className="rail">
          <h2 className="section-title">
            Start building transparent agent workflows.
          </h2>
          <p className="lead">
            Open source, inspectable, and built for developers who value
            ownership.
          </p>
          <Link
            className="button primary"
            href="https://github.com/gaedsstudio/sovyn"
          >
            Get Started with SOVYN
          </Link>
        </div>
      </section>
    </>
  );
}
