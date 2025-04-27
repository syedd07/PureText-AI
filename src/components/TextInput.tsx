
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { ClipboardPaste, X } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

interface TextInputProps {
  onSubmit: (text: string) => void;
}

const TextInput = ({ onSubmit }: TextInputProps) => {
  const [text, setText] = useState('');
  const { toast } = useToast();

  const handleSubmit = () => {
    if (text.trim()) {
      onSubmit(text);
    }
  };

  const handlePaste = async () => {
    try {
      const text = await navigator.clipboard.readText();
      setText(text);
      toast({
        description: "Text pasted from clipboard",
      });
    } catch (err) {
      toast({
        variant: "destructive",
        description: "Failed to read from clipboard",
      });
    }
  };

  const handleClear = () => {
    setText('');
    toast({
      description: "Text cleared",
    });
  };

  return (
    <div className="space-y-4 animate-fade-in">
      <div className="relative">
        <Textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Paste your text here to check for plagiarism..."
          className="min-h-[200px] p-4 pr-12 resize-y"
        />
        {text && (
          <Button
            size="icon"
            variant="ghost"
            className="absolute right-2 top-2 opacity-70 hover:opacity-100"
            onClick={handleClear}
          >
            <X className="h-4 w-4" />
          </Button>
        )}
      </div>
      <div className="flex justify-between items-center flex-wrap gap-4">
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            className="gap-2"
            onClick={handlePaste}
          >
            <ClipboardPaste className="h-4 w-4" />
            Paste from Clipboard
          </Button>
          <span className="text-sm text-muted-foreground">
            {text.length} characters
          </span>
        </div>
        <Button 
          onClick={handleSubmit}
          disabled={!text.trim()}
          className="min-w-[150px]"
        >
          Check Plagiarism
        </Button>
      </div>
    </div>
  );
};

export default TextInput;
