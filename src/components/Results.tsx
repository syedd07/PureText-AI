import { Progress } from '@/components/ui/progress';
import { ExternalLink } from 'lucide-react';

interface ResultsProps {
  plagiarismPercentage: number;
  matches: Array<{
    textSnippet: string;
    sourceUrl: string;
    similarityScore?: number;
  }>;
  fullTextWithHighlights: string;
}

const Results = ({ plagiarismPercentage, matches, fullTextWithHighlights }: ResultsProps) => {
  // Add a message for no matches
  const hasMatches = matches && matches.length > 0;
  
  return (
    <div className="bg-white rounded-lg shadow-sm border p-6 space-y-8 animate-fade-in">
      <div className="p-6 bg-white rounded-lg shadow-sm border">
        <h2 className="text-xl font-semibold mb-4">Plagiarism Score</h2>
        <div className="space-y-2">
          <Progress value={plagiarismPercentage} className="h-4" />
          <p className="text-sm text-gray-600">
            {plagiarismPercentage}% of your text matches other sources
          </p>
        </div>
      </div>

      <div className="space-y-4">
        <h3 className="text-xl font-semibold text-gray-800">Matched Sources</h3>
        
        {hasMatches ? (
          <div className="space-y-4">
            {matches.map((match, index) => (
              <div key={index} className="p-4 border rounded-lg">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-sm mb-2 italic text-muted-foreground">
                      Matched text:
                    </p>
                    <p className="text-gray-800">{match.textSnippet}</p>
                  </div>
                  <div className="bg-primary/10 text-primary font-medium px-2 py-1 rounded text-sm">
                    {(match.similarityScore * 100).toFixed(0)}% match
                  </div>
                </div>
                <a href={match.sourceUrl} target="_blank" rel="noopener noreferrer" 
                   className="mt-2 text-primary hover:underline text-sm flex items-center">
                  View source <ExternalLink className="ml-1 h-3 w-3" />
                </a>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-4 border rounded-lg bg-gray-50 text-center">
            <p className="text-muted-foreground">
              No matching sources found. Your content appears to be original.
            </p>
          </div>
        )}
      </div>

      <div className="space-y-4">
        <h3 className="text-xl font-semibold text-gray-800">Full Text Analysis</h3>
        <div 
          className="border rounded-lg p-4 prose max-w-none"
          dangerouslySetInnerHTML={{ __html: fullTextWithHighlights }}
        />
      </div>
    </div>
  );
};

export default Results;
