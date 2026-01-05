/**
 * Terms of Service Page
 *
 * Legal terms and conditions for using SceneMachine Network.
 */

import React from 'react';
import Link from 'next/link';

export default function TermsPage() {
  return (
    <div className="legal-page">
      <header className="header">
        <Link href="/" className="logo">
          SceneMachine
        </Link>
        <nav className="nav">
          <Link href="/terms" className="active">Terms</Link>
          <Link href="/privacy">Privacy</Link>
        </nav>
      </header>

      <main className="content">
        <article className="legal-content">
          <h1>Terms of Service</h1>
          <p className="last-updated">Last updated: December 31, 2025</p>

          <section>
            <h2>1. Acceptance of Terms</h2>
            <p>
              By accessing or using SceneMachine Network ("the Service"), you agree to be bound by these
              Terms of Service ("Terms"). If you do not agree to these Terms, you may not use the Service.
            </p>
            <p>
              SceneMachine Network is operated by SceneMachine, Inc. ("we", "us", or "our"). These Terms
              govern your access to and use of our website, applications, and services.
            </p>
          </section>

          <section>
            <h2>2. Description of Service</h2>
            <p>
              SceneMachine Network is a video streaming and social platform designed for independent
              filmmakers and content creators. The Service allows users to:
            </p>
            <ul>
              <li>Upload, share, and monetize video content</li>
              <li>Discover and watch videos from other creators</li>
              <li>Follow creators and engage with content through comments and reactions</li>
              <li>Earn revenue through advertising, ticket sales, tips, and subscriptions</li>
            </ul>
          </section>

          <section>
            <h2>3. User Accounts</h2>
            <h3>3.1 Account Creation</h3>
            <p>
              To use certain features of the Service, you must create an account. You agree to provide
              accurate, current, and complete information during registration and to update such
              information to keep it accurate.
            </p>
            <h3>3.2 Account Security</h3>
            <p>
              You are responsible for maintaining the confidentiality of your account credentials and
              for all activities that occur under your account. You must immediately notify us of any
              unauthorized use of your account.
            </p>
            <h3>3.3 Account Termination</h3>
            <p>
              We reserve the right to suspend or terminate your account at any time for violations of
              these Terms or for any other reason at our discretion.
            </p>
          </section>

          <section>
            <h2>4. Content Guidelines</h2>
            <h3>4.1 Your Content</h3>
            <p>
              You retain ownership of all content you upload to the Service ("Your Content"). By
              uploading content, you grant us a worldwide, non-exclusive, royalty-free license to
              use, reproduce, modify, adapt, publish, and display Your Content for the purpose of
              operating and providing the Service.
            </p>
            <h3>4.2 Prohibited Content</h3>
            <p>You agree not to upload, post, or share content that:</p>
            <ul>
              <li>Infringes on intellectual property rights of others</li>
              <li>Contains illegal, harmful, threatening, abusive, or defamatory material</li>
              <li>Depicts violence, exploitation, or abuse of minors</li>
              <li>Contains sexually explicit material without proper age restrictions</li>
              <li>Promotes hatred, discrimination, or violence against individuals or groups</li>
              <li>Contains malware, viruses, or other harmful code</li>
              <li>Violates any applicable laws or regulations</li>
            </ul>
            <h3>4.3 Content Moderation</h3>
            <p>
              We reserve the right to review, remove, or restrict access to any content that violates
              these Terms or our Community Guidelines. We may use automated systems to detect and
              remove prohibited content.
            </p>
          </section>

          <section>
            <h2>5. Creator Monetization</h2>
            <h3>5.1 Revenue Sharing</h3>
            <p>
              Eligible creators may earn revenue through the Service. Our revenue sharing model is
              graduated based on lifetime earnings:
            </p>
            <ul>
              <li>$0 - $1,000: 50% creator share</li>
              <li>$1,001 - $10,000: 60% creator share</li>
              <li>$10,001 - $100,000: 70% creator share</li>
              <li>$100,001 - $1,000,000: 80% creator share</li>
              <li>$1,000,001 - $10,000,000: 90% creator share</li>
              <li>$10,000,001+: 99% creator share</li>
            </ul>
            <h3>5.2 Payment Terms</h3>
            <p>
              Payouts are processed monthly for creators who have reached the minimum payout threshold
              of $100. You are responsible for providing accurate payment information and for any
              applicable taxes on your earnings.
            </p>
            <h3>5.3 Cost Transparency</h3>
            <p>
              Content must be self-sustaining, meaning it must generate enough revenue to cover its
              storage and bandwidth costs. We provide detailed cost breakdowns to help creators
              understand their content economics.
            </p>
          </section>

          <section>
            <h2>6. Intellectual Property</h2>
            <p>
              The Service, including its design, features, and content (excluding user-generated
              content), is owned by SceneMachine, Inc. and is protected by copyright, trademark,
              and other intellectual property laws.
            </p>
            <p>
              You may not copy, modify, distribute, or create derivative works of any part of the
              Service without our express written permission.
            </p>
          </section>

          <section>
            <h2>7. DMCA and Copyright</h2>
            <p>
              We respect the intellectual property rights of others. If you believe your copyrighted
              work has been infringed on our Service, please submit a DMCA takedown notice to our
              designated copyright agent.
            </p>
            <p>
              Repeat infringers will have their accounts terminated in accordance with our policies.
            </p>
          </section>

          <section>
            <h2>8. Disclaimer of Warranties</h2>
            <p>
              THE SERVICE IS PROVIDED "AS IS" AND "AS AVAILABLE" WITHOUT WARRANTIES OF ANY KIND,
              EITHER EXPRESS OR IMPLIED. WE DO NOT WARRANT THAT THE SERVICE WILL BE UNINTERRUPTED,
              ERROR-FREE, OR SECURE.
            </p>
          </section>

          <section>
            <h2>9. Limitation of Liability</h2>
            <p>
              TO THE MAXIMUM EXTENT PERMITTED BY LAW, SCENEMACHINE, INC. SHALL NOT BE LIABLE FOR ANY
              INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES ARISING OUT OF OR
              RELATED TO YOUR USE OF THE SERVICE.
            </p>
          </section>

          <section>
            <h2>10. Indemnification</h2>
            <p>
              You agree to indemnify and hold harmless SceneMachine, Inc. and its officers, directors,
              employees, and agents from any claims, damages, losses, or expenses arising from your
              use of the Service or violation of these Terms.
            </p>
          </section>

          <section>
            <h2>11. Changes to Terms</h2>
            <p>
              We may update these Terms from time to time. We will notify you of material changes by
              posting the new Terms on this page and updating the "Last updated" date. Your continued
              use of the Service after such changes constitutes acceptance of the new Terms.
            </p>
          </section>

          <section>
            <h2>12. Governing Law</h2>
            <p>
              These Terms shall be governed by and construed in accordance with the laws of the State
              of California, without regard to its conflict of law provisions.
            </p>
          </section>

          <section>
            <h2>13. Contact Us</h2>
            <p>
              If you have any questions about these Terms, please contact us at:
            </p>
            <p>
              <strong>Email:</strong> legal@scenemachine.com<br />
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
