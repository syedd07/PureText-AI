
import { Progress } from '@/components/ui/progress';
import { ExternalLink, ArrowRight, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert';

interface ResultsProps {
  plagiarismPercentage: number;
  matches: Array<{
    textSnippet: string;
    sourceUrl: string;
    similarityScore?: number;
  }>;
  fullTextWithHighlights: string;
  onScanAnother?: () => void;
}

const Results = ({ plagiarismPercentage, matches, fullTextWithHighlights, onScanAnother }: ResultsProps) => {
  const hasMatches = matches && matches.length > 0;
  const plagiarismLevel = plagiarismPercentage <= 20 ? 'low' : plagiarismPercentage <= 50 ? 'medium' : 'high';
  
  const getPlagiarismFeedback = () => {
    if (plagiarismPercentage <= 20) {
      return {
        icon: <CheckCircle2 className="h-5 w-5 text-green-500" />,
        title: 'Low Plagiarism Detected',
        description: 'Your content appears to be mostly original.',
        color: 'bg-green-500'
      };
    } else if (plagiarismPercentage <= 50) {
      return {
        icon: <AlertTriangle className="h-5 w-5 text-yellow-500" />,
        title: 'Moderate Plagiarism Detected',
        description: 'Some sections of your content match other sources.',
        color: 'bg-yellow-500'
      };
    } else {
      return {
        icon: <AlertTriangle className="h-5 w-5 text-red-500" />,
        title: 'High Plagiarism Detected',
        description: 'Significant portions of your content match other sources.',
        color: 'bg-red-500'
      };
    }
  };

  const feedback = getPlagiarismFeedback();

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-fade-in">
      <div className="bg-white rounded-lg shadow-lg border p-8">
        {/* Score Section */}
        <div className="space-y-6">
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <h2 className="text-2xl font-semibold flex items-center gap-2">
                {feedback.icon}
                {feedback.title}
              </h2>
              <p className="text-muted-foreground">{feedback.description}</p>
            </div>
            
            <Button onClick={onScanAnother} variant="outline" className="hover:bg-secondary">
              Scan Another
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </div>

          <div className="space-y-2">
            <div className="flex justify-between text-sm mb-1">
              <span>Similarity Score</span>
              <span className="font-medium">{plagiarismPercentage}%</span>
            </div>
            <Progress 
              value={plagiarismPercentage} 
              className={`h-3 ${feedback.color}`}
            />
          </div>
        </div>

        {/* Results Alert */}
        <Alert className="mt-6 bg-secondary/50">
          <AlertTitle className="text-foreground">Analysis Complete</AlertTitle>
          <AlertDescription>
            {hasMatches 
              ? `Found ${matches.length} matching ${matches.length === 1 ? 'source' : 'sources'} in your content.`
              : 'No matching sources found in your content.'}
          </AlertDescription>
        </Alert>
      </div>

      {/* Matched Sources Section */}
      <div className="bg-white rounded-lg shadow-lg border p-8">
        <h3 className="text-xl font-semibold mb-6">Matched Sources</h3>
        
        {hasMatches ? (
          <div className="space-y-4">
            {matches.map((match, index) => (
              <div key={index} className="p-6 border rounded-lg bg-secondary/20 hover:bg-secondary/30 transition-colors">
                <div className="flex justify-between items-start gap-4">
                  <div className="space-y-2 flex-1">
                    <p className="text-sm text-muted-foreground">Matched text:</p>
                    <p className="text-foreground">{match.textSnippet}</p>
                    <a 
                      href={match.sourceUrl} 
                      target="_blank" 
                      rel="noopener noreferrer" 
                      className="inline-flex items-center text-primary hover:underline mt-2 text-sm"
                    >
                      View source <ExternalLink className="ml-1 h-3 w-3" />
                    </a>
                  </div>
                  <div className="bg-primary/10 text-primary font-medium px-3 py-1 rounded-full text-sm whitespace-nowrap">
                    {(match.similarityScore * 100).toFixed(0)}% match
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-6 border rounded-lg bg-green-50 text-center">
            <p className="text-green-800">
              No matching sources found. Your content appears to be original.
            </p>
          </div>
        )}
      </div>

      {/* Full Text Analysis Section */}
      <div className="bg-white rounded-lg shadow-lg border p-8">
        <h3 className="text-xl font-semibold mb-6">Full Text Analysis</h3>
        <div 
          className="prose max-w-none p-6 border rounded-lg bg-secondary/10"
          dangerouslySetInnerHTML={{ __html: fullTextWithHighlights }}
        />
      </div>
    </div>
  );
};

export default Results;