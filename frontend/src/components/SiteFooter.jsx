import { GithubLogo, Heart, Plant } from "@phosphor-icons/react";

export default function SiteFooter({ onDemo }) {
  return (
    <footer className="site-footer">
      <div className="foot-grid">
        <div>
          <p className="wordmark">
            <Plant size={18} weight="fill" aria-hidden="true" />
            Moss Garden
          </p>
          <p>Small commits. Slow growth. A garden that remembers.</p>
        </div>
        <nav aria-label="Product">
          <h2>Product</h2>
          <a href="#how">How it grows</a>
          <button type="button" onClick={onDemo}>Demo garden</button>
          <a href="#journal">Journal</a>
        </nav>
        <nav aria-label="Trust">
          <h2>Trust</h2>
          <a href="#privacy">Privacy</a>
          <a href="#privacy">GitHub permissions</a>
          <a href="#model">Model notes</a>
        </nav>
        <nav aria-label="More">
          <h2>More</h2>
          <a href="#faq">FAQ</a>
          <a href="#faq">Accessibility</a>
          <a href="https://github.com/ADITYA-KUMAR-2358" target="_blank" rel="noopener noreferrer">Contact</a>
        </nav>
      </div>
      <div className="signature">
        <p>
          Built by Aditya Kumar
          <Heart className="heart" size={18} weight="fill" aria-hidden="true" />
        </p>
        <a
          className="secondary"
          href="https://github.com/ADITYA-KUMAR-2358"
          target="_blank"
          rel="noopener noreferrer"
          aria-label="Aditya on GitHub (opens in a new tab)"
        >
          <GithubLogo size={20} weight="fill" aria-hidden="true" />
          Aditya on GitHub
        </a>
      </div>
    </footer>
  );
}
