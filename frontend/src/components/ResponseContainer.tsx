import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
// SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
// SPDX-License-Identifier: MIT

interface ResponseContainerProps {
  content: string;
}

const ResponseContainer: React.FC<ResponseContainerProps> = ({ content }) => {
  // Handle empty content to avoid rendering empty containers
  if (!content) return null;

  return (
    <div className="response-container">
      {/* Security: Content comes from trusted backend API responses.
         If external/untrusted sources are added, consider rehype-sanitize for XSS protection. */}
      <div
        style={{
          lineHeight: '1.6',
          color: 'var(--text)',
          fontSize: '1rem'
        }}
      >
        {/* Custom components provide consistent styling for markdown elements,
           overriding default browser styles with Tailwind classes */}
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            h1: ({ node, ...props }) => <h1 className="text-2xl font-bold my-4" {...props} />,
            h2: ({ node, ...props }) => <h2 className="text-xl font-bold my-3" {...props} />,
            h3: ({ node, ...props }) => <h3 className="text-lg font-bold my-2" {...props} />,
            h4: ({ node, ...props }) => <h4 className="text-base font-bold my-2" {...props} />,
            h5: ({ node, ...props }) => <h5 className="text-sm font-bold my-1" {...props} />,
            h6: ({ node, ...props }) => <h6 className="text-xs font-bold my-1" {...props} />,
            p: ({ node, ...props }) => <p className="my-2" {...props} />,
            ul: ({ node, ...props }) => <ul className="list-disc list-inside ml-4 my-2" {...props} />,
            ol: ({ node, ...props }) => <ol className="list-decimal list-inside ml-4 my-2" {...props} />,
            li: ({ node, ...props }) => <li className="my-1" {...props} />,
            blockquote: ({ node, ...props }) => <blockquote className="border-l-4 border-gray-300 pl-4 italic my-2" {...props} />,
            code: ({ node, ...props }) =>
              (props as Record<string, unknown>).inline ? (
                <code className="bg-gray-100 dark:bg-gray-800 px-1 py-0.5 rounded text-sm font-mono" {...props} />
              ) : (
                <code className="block bg-gray-100 dark:bg-gray-800 p-4 rounded text-sm font-mono overflow-x-auto my-2" {...props} />
              ),
            pre: ({ node, ...props }) => <pre className="bg-gray-100 dark:bg-gray-800 p-4 rounded overflow-x-auto my-2" {...props} />,
            strong: ({ node, ...props }) => <strong className="font-bold" {...props} />,
            em: ({ node, ...props }) => <em className="italic" {...props} />,
            a: ({ node, ...props }) => <a className="text-blue-600 hover:text-blue-800 underline" {...props} />,
            table: ({ node, ...props }) => <table className="border-collapse border border-gray-300 my-2" {...props} />,
            thead: ({ node, ...props }) => <thead className="bg-gray-100 dark:bg-gray-800" {...props} />,
            tbody: ({ node, ...props }) => <tbody {...props} />,
            tr: ({ node, ...props }) => <tr className="border-b border-gray-300" {...props} />,
            th: ({ node, ...props }) => <th className="border border-gray-300 px-4 py-2 text-left font-bold" {...props} />,
            td: ({ node, ...props }) => <td className="border border-gray-300 px-4 py-2" {...props} />,
            del: ({ node, ...props }) => <del className="line-through" {...props} />,
          }}
        >
          {content}
        </ReactMarkdown>
      </div>
    </div>
  );
};

export default ResponseContainer;
