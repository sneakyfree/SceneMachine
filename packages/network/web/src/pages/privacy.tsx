/**
 * Privacy Policy Page
 *
 * Privacy policy and data handling practices for SceneMachine Network.
 */

import React from 'react';
import Link from 'next/link';

export default function PrivacyPage() {
  return (
    <div className="legal-page">
      <header className="header">
        <Link href="/" className="logo">
          SceneMachine
        </Link>
        <nav className="nav">
          <Link href="/terms">Terms</Link>
          <Link href="/privacy" className="active">Privacy</Link>
        </nav>
      </header>

      <main className="content">
        <article className="legal-content">
          <h1>Privacy Policy</h1>
          <p className="last-updated">Last updated: December 31, 2025</p>

          <section>
            <h2>1. Introduction</h2>
            <p>
              SceneMachine, Inc. ("we", "us", or "our") operates the SceneMachine Network platform.
              This Privacy Policy explains how we collect, use, disclose, and safeguard your
              information when you use our Service.
            </p>
            <p>
              We are committed to protecting your privacy and ensuring you understand how your data
              is handled. Please read this policy carefully.
            </p>
          </section>

          <section>
            <h2>2. Information We Collect</h2>

            <h3>2.1 Information You Provide</h3>
            <p>We collect information you directly provide to us, including:</p>
            <ul>
              <li><strong>Account Information:</strong> Email address, username, display name, password, and profile picture</li>
              <li><strong>Content:</strong> Videos, images, comments, and other content you upload or create</li>
              <li><strong>Communications:</strong> Messages and correspondence with us or other users</li>
              <li><strong>Payment Information:</strong> For creators, payment details for receiving earnings (processed by Stripe)</li>
            </ul>

            <h3>2.2 Information Collected Automatically</h3>
            <p>When you use our Service, we automatically collect:</p>
            <ul>
              <li><strong>Usage Data:</strong> Pages viewed, videos watched, watch time, interactions, and preferences</li>
              <li><strong>Device Information:</strong> Device type, operating system, browser type, and unique identifiers</li>
              <li><strong>Log Data:</strong> IP address, access times, referring URLs, and error logs</li>
              <li><strong>Cookies:</strong> Session cookies, preference cookies, and analytics cookies</li>
            </ul>

            <h3>2.3 Information from Third Parties</h3>
            <p>We may receive information from:</p>
            <ul>
              <li>Social media platforms if you choose to link your accounts</li>
              <li>Payment processors regarding transaction status</li>
              <li>Analytics providers about aggregate usage patterns</li>
            </ul>
          </section>

          <section>
            <h2>3. How We Use Your Information</h2>
            <p>We use the information we collect to:</p>
            <ul>
              <li>Provide, maintain, and improve our Service</li>
              <li>Process transactions and send related information</li>
              <li>Personalize your experience and content recommendations</li>
              <li>Send you technical notices, updates, and support messages</li>
              <li>Respond to your comments, questions, and requests</li>
              <li>Monitor and analyze trends, usage, and activities</li>
              <li>Detect, investigate, and prevent fraudulent or illegal activities</li>
              <li>Comply with legal obligations</li>
            </ul>
          </section>

          <section>
            <h2>4. Sharing of Information</h2>

            <h3>4.1 Public Information</h3>
            <p>
              Some information is public by default, including your username, profile picture,
              public videos, and comments. This information is visible to all users.
            </p>

            <h3>4.2 Service Providers</h3>
            <p>
              We share information with third-party service providers who perform services on our
              behalf, including:
            </p>
            <ul>
              <li>Cloud hosting providers (AWS, Cloudflare)</li>
              <li>Payment processors (Stripe)</li>
              <li>Analytics services</li>
              <li>Content delivery networks</li>
            </ul>

            <h3>4.3 Legal Requirements</h3>
            <p>
              We may disclose information if required to do so by law or in response to valid
              requests by public authorities.
            </p>

            <h3>4.4 Business Transfers</h3>
            <p>
              In the event of a merger, acquisition, or sale of assets, your information may be
              transferred as part of that transaction.
            </p>
          </section>

          <section>
            <h2>5. Data Retention</h2>
            <p>
              We retain your information for as long as your account is active or as needed to
              provide you services. We may retain certain information as required by law or for
              legitimate business purposes.
            </p>
            <p>
              You can request deletion of your account and associated data at any time through
              your account settings or by contacting us.
            </p>
          </section>

          <section>
            <h2>6. Security</h2>
            <p>
              We implement appropriate technical and organizational measures to protect your
              information, including:
            </p>
            <ul>
              <li>Encryption of data in transit and at rest</li>
              <li>Regular security assessments and audits</li>
              <li>Access controls and authentication measures</li>
              <li>Secure development practices</li>
            </ul>
            <p>
              However, no method of transmission over the Internet is 100% secure. We cannot
              guarantee absolute security of your data.
            </p>
          </section>

          <section>
            <h2>7. Your Rights and Choices</h2>

            <h3>7.1 Account Settings</h3>
            <p>
              You can access, update, or delete your account information through your account
              settings at any time.
            </p>

            <h3>7.2 Privacy Controls</h3>
            <p>You can control:</p>
            <ul>
              <li>Whether your subscriber count is publicly visible</li>
              <li>Whether your watch history is used for recommendations</li>
              <li>Email and push notification preferences</li>
            </ul>

            <h3>7.3 Data Access and Portability</h3>
            <p>
              You can request a copy of your data in a portable format through your account
              settings or by contacting us.
            </p>

            <h3>7.4 Deletion</h3>
            <p>
              You can request deletion of your account and personal data. Some information may
              be retained as required by law or for legitimate business purposes.
            </p>

            <h3>7.5 Cookies</h3>
            <p>
              Most browsers allow you to refuse cookies or alert you when cookies are being sent.
              Note that some features of our Service may not function properly without cookies.
            </p>
          </section>

          <section>
            <h2>8. Children's Privacy</h2>
            <p>
              Our Service is not intended for children under 13 years of age. We do not knowingly
              collect personal information from children under 13. If we become aware that we have
              collected information from a child under 13, we will take steps to delete that
              information.
            </p>
          </section>

          <section>
            <h2>9. International Data Transfers</h2>
            <p>
              Your information may be transferred to and processed in countries other than your
              own. We ensure appropriate safeguards are in place to protect your information in
              compliance with applicable data protection laws.
            </p>
          </section>

          <section>
            <h2>10. California Privacy Rights</h2>
            <p>
              If you are a California resident, you have additional rights under the California
              Consumer Privacy Act (CCPA), including:
            </p>
            <ul>
              <li>The right to know what personal information is collected</li>
              <li>The right to request deletion of personal information</li>
              <li>The right to opt-out of the sale of personal information (we do not sell your data)</li>
              <li>The right to non-discrimination for exercising your rights</li>
            </ul>
          </section>

          <section>
            <h2>11. European Privacy Rights</h2>
            <p>
              If you are located in the European Economic Area (EEA), you have additional rights
              under the General Data Protection Regulation (GDPR), including:
            </p>
            <ul>
              <li>Right of access to your personal data</li>
              <li>Right to rectification of inaccurate data</li>
              <li>Right to erasure ("right to be forgotten")</li>
              <li>Right to restriction of processing</li>
              <li>Right to data portability</li>
              <li>Right to object to processing</li>
            </ul>
            <p>
              To exercise these rights, please contact us at privacy@scenemachine.com.
            </p>
          </section>

          <section>
            <h2>12. Changes to This Policy</h2>
            <p>
              We may update this Privacy Policy from time to time. We will notify you of material
              changes by posting the new policy on this page and updating the "Last updated" date.
              We encourage you to review this policy periodically.
            </p>
          </section>

          <section>
            <h2>13. Contact Us</h2>
            <p>
              If you have questions about this Privacy Policy or our privacy practices, please
              contact us at:
            </p>
            <p>
              <strong>Email:</strong> privacy@scenemachine.com<br />
              <strong>Data Protection Officer:</strong> dpo@scenemachine.com<br />
              <strong>Address:</strong> SceneMachine, Inc., San Francisco, CA
            </p>
          </section>
        </article>
      </main>

      <footer className="footer">
        <p>&copy; 2025 SceneMachine, Inc. All rights reserved.</p>
        <nav>
          <Link href="/terms">Terms</Link>
          <Link href="/privacy">Privacy</Link>
          <Link href="/">Home</Link>
        </nav>
      </footer>

      <style jsx>{`
        .legal-page {
          min-height: 100vh;
          background: var(--color-bg-primary);
          display: flex;
          flex-direction: column;
        }

        .header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: var(--space-4) var(--space-6);
          border-bottom: 1px solid var(--color-border);
          background: var(--color-bg-secondary);
        }

        .logo {
          font-size: var(--text-xl);
          font-weight: 700;
          background: var(--gradient-primary);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          text-decoration: none;
        }

        .nav {
          display: flex;
          gap: var(--space-4);
        }

        .nav a {
          color: var(--color-text-secondary);
          font-weight: 500;
          padding: var(--space-2) var(--space-3);
          border-radius: var(--radius-md);
        }

        .nav a:hover {
          color: var(--color-text-primary);
        }

        .nav a.active {
          color: var(--color-accent);
          background: var(--color-accent-light);
        }

        .content {
          flex: 1;
          max-width: 800px;
          margin: 0 auto;
          padding: var(--space-8) var(--space-4);
        }

        .legal-content h1 {
          font-size: var(--text-3xl);
          margin-bottom: var(--space-2);
        }

        .last-updated {
          color: var(--color-text-tertiary);
          font-size: var(--text-sm);
          margin-bottom: var(--space-8);
        }

        section {
          margin-bottom: var(--space-8);
        }

        section h2 {
          font-size: var(--text-xl);
          margin-bottom: var(--space-4);
          padding-bottom: var(--space-2);
          border-bottom: 1px solid var(--color-border);
        }

        section h3 {
          font-size: var(--text-lg);
          margin-top: var(--space-4);
          margin-bottom: var(--space-2);
        }

        section p {
          color: var(--color-text-secondary);
          line-height: var(--leading-relaxed);
          margin-bottom: var(--space-3);
        }

        section ul {
          margin-left: var(--space-6);
          margin-bottom: var(--space-4);
        }

        section li {
          color: var(--color-text-secondary);
          line-height: var(--leading-relaxed);
          margin-bottom: var(--space-2);
        }

        .footer {
          padding: var(--space-6);
          border-top: 1px solid var(--color-border);
          background: var(--color-bg-secondary);
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .footer p {
          color: var(--color-text-tertiary);
          font-size: var(--text-sm);
        }

        .footer nav {
          display: flex;
          gap: var(--space-4);
        }

        .footer nav a {
          color: var(--color-text-tertiary);
          font-size: var(--text-sm);
        }

        .footer nav a:hover {
          color: var(--color-accent);
        }

        @media (max-width: 640px) {
          .header {
            flex-direction: column;
            gap: var(--space-3);
          }

          .content {
            padding: var(--space-6) var(--space-4);
          }

          .footer {
            flex-direction: column;
            gap: var(--space-4);
            text-align: center;
          }
        }
      `}</style>
    </div>
  );
}
