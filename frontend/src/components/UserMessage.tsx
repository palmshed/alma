// SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
// SPDX-License-Identifier: MIT
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
