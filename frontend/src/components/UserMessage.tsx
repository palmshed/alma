import React from 'react';

interface UserMessageProps {
  content: string;
}

const UserMessage: React.FC<UserMessageProps> = ({ content }) => {
  if (!content) return null;

  return (
    <div className="user-message">{content}</div>
  );
};

export default UserMessage;
