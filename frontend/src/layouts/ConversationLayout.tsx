import { ReactNode } from 'react';

interface ConversationLayoutProps {
  messages: ReactNode;
  composer: ReactNode;
  sidebar?: ReactNode;
  scrollRef?: React.MutableRefObject<HTMLDivElement | null>;
}

export default function ConversationLayout({ messages, composer, scrollRef }: ConversationLayoutProps) {
  return (
    <div className="conversation-layout">
      <div className="conversation-scroll" ref={scrollRef as React.Ref<HTMLDivElement>}>
        {messages}
      </div>
      <div className="conversation-composer">
        {composer}
      </div>
    </div>
  );
}
