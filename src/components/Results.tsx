
import { Progress } from '@/components/ui/progress';

interface ResultsProps {
  plagiarismPercentage: number;
  matches: Array<{ textSnippet: string; sourceUrl: string }>;
  fullTextWithHighlights: string;
}

const Results = ({ plagiarismPercentage, matches, fullTextWithHighlights }: ResultsProps) => {
  return (
    <div className="space-y-8 animate-fade-in">
      <div className="p-6 bg-white rounded-lg shadow-sm border">
        <h2 className="text-xl font-semibold mb-4">Plagiarism Score</h2>
        <div className="space-y-2">
          <Progress value={plagiarismPercentage} className="h-4" />
          <p className="text-sm text-gray-600">
            {plagiarismPercentage}% of your text matches other sources
          </p>
        </div>
      </div>

      <div className="p-6 bg-white rounded-lg shadow-sm border">
        <h2 className="text-xl font-semibold mb-4">Matched Sources</h2>
        <div className="space-y-4">
          {matches.map((match, index) => (
            <div key={index} className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-800 mb-2">{match.textSnippet}</p>
              <a
                href={match.sourceUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary hover:underline text-sm"
              >
                {match.sourceUrl}
              </a>
            </div>
          ))}
        </div>
      </div>

      <div className="p-6 bg-white rounded-lg shadow-sm border">
        <h2 className="text-xl font-semibold mb-4">Full Text Analysis</h2>
        <div
          className="prose max-w-none"
          dangerouslySetInnerHTML={{ __html: fullTextWithHighlights }}
        />
      </div>
    </div>
  );
};

export default Results;
