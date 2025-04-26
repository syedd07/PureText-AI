
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';

interface TextInputProps {
  onSubmit: (text: string) => void;
}

const TextInput = ({ onSubmit }: TextInputProps) => {
  const [text, setText] = useState('');

  const handleSubmit = () => {
    if (text.trim()) {
      onSubmit(text);
    }
  };

  return (
    <div className="space-y-4">
      <Textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Paste your text here to check for plagiarism..."
        className="min-h-[200px] p-4"
      />
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-500">
          {text.length} characters
        </span>
        <Button 
          onClick={handleSubmit}
          disabled={!text.trim()}
        >
          Check Plagiarism
        </Button>
      </div>
    </div>
  );
};

export default TextInput;
