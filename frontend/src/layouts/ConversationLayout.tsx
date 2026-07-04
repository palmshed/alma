import { ReactNode } from 'react';

interface ConversationLayoutProps {
  messages: ReactNode;
  composer: ReactNode;
  sidebar?: ReactNode;
}

export default function ConversationLayout({ messages, composer }: ConversationLayoutProps) {
  return (
    <div className="conversation-layout">
      <div className="conversation-scroll">
        {messages}
      </div>
      <div className="conversation-composer">
        {composer}
      </div>
    </div>
  );
}
