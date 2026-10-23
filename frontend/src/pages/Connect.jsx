import { CheckCircle, GithubLogo, WarningCircle } from "@phosphor-icons/react";
import { PlantMark } from "../components/GardenScene.jsx";

const COPY = {
  ready: {
    title: "Sign in with GitHub",
    body: "Use your own GitHub account. Moss Garden reads commits you authored and grows your garden from them. It can't write to GitHub, and you never paste a client id or secret.",
  },
  setup: {
    title: "Turn on GitHub sign-in",
    body: "Players sign in with their own GitHub accounts. This server still needs its app approved once, by the person running Moss Garden. After that, the client id stays on the server.",
  },
  importing: {
    title: "Gathering your history",
    body: "Reading your last 12 months of public activity. This usually takes under a minute. You can leave this page.",
  },
  success: {
    title: "Your garden has started",
    body: "We found your eligible activity and planted the first seeds. Some may already have sprouted.",
  },
  error: {
    title: "GitHub didn't answer",
    body: "Nothing was changed. This is usually temporary.",
  },
};

export default function Connect({ phase, detail, githubReady, onContinue, onDemo, onRetry, onGarden }) {
  const signingIn = phase === "ready" && githubReady;
  const copy = (phase === "ready" && !githubReady ? COPY.setup : COPY[phase]) || COPY.ready;
  return (
    <main id="content" className="page connect-page">
      <article className="connect-card">
        <PlantMark species="clover" stage="sprout" size={96} />
        <h1>{copy.title}</h1>
        <p>{copy.body}</p>
        {phase === "ready" ? (
          <>
            <p className="mono scope">{signingIn ? "read:user public_repo" : "one-time server setup"}</p>
            <p className="caption">
              {signingIn
                ? "GitHub asks you to approve read access. Your public repositories are planted first. You can change that list in Settings."
                : "This button opens GitHub so you can approve the Moss Garden app. Players who visit later only see Sign in with GitHub."}
            </p>
            <button type="button" className="primary" onClick={onContinue}>
              <GithubLogo size={18} weight="fill" aria-hidden="true" />
              {signingIn ? "Sign in with GitHub" : "Approve GitHub sign-in"}
            </button>
            <button type="button" className="text-link" onClick={onDemo}>Explore a demo garden instead</button>
          </>
        ) : null}
        {phase === "importing" ? (
          <div className="track" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={40} aria-label="Import progress">
            <span style={{ width: "40%" }} />
          </div>
        ) : null}
        {phase === "success" ? (
          <>
            <p className="saved"><CheckCircle size={18} weight="fill" aria-hidden="true" /> Saved</p>
            <button type="button" className="primary" onClick={onGarden}>See my garden</button>
          </>
        ) : null}
        {phase === "error" ? (
          <>
            <p className="danger" role="alert">
              <WarningCircle size={18} weight="fill" aria-hidden="true" />
              {detail || "GitHub sign-in needs a client id, a client secret, and a token key in backend/.env."}
            </p>
            <div className="actions">
              <button type="button" className="primary" onClick={onRetry}>Try again</button>
              <button type="button" className="secondary" onClick={onDemo}>Explore a demo garden</button>
            </div>
          </>
        ) : null}
      </article>
    </main>
  );
}
