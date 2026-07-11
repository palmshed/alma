import React, { ReactNode } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
// SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
// SPDX-License-Identifier: MIT

interface ResponseContainerProps {
  content: string;
  children?: ReactNode;
}

const ResponseContainer: React.FC<ResponseContainerProps> = ({ content, children }) => {
  // Handle empty content to avoid rendering empty containers
  if (!content) return null;

  return (
    <div className="response-container">
      {/* Security: Content comes from trusted backend API responses.
         If external/untrusted sources are added, consider rehype-sanitize for XSS protection. */}
      <div className="markdown-content">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            p: ({ node, ...props }) => <p {...props} />,
            blockquote: ({ node, ...props }) => <blockquote {...props} />,
            code: ({ node, ...props }) =>
              (props as Record<string, unknown>).inline ? (
                <code {...props} />
              ) : (
                <code {...props} />
              ),
            pre: ({ node, ...props }) => <pre {...props} />,
            strong: ({ node, ...props }) => <strong {...props} />,
            em: ({ node, ...props }) => <em {...props} />,
            a: ({ node, ...props }) => <a {...props} />,
            del: ({ node, ...props }) => <del {...props} />,
          }}
        >
          {content}
        </ReactMarkdown>
      </div>
      {children}
    </div>
  );
};

export default ResponseContainer;
