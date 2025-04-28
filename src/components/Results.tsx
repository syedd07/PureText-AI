import { Progress } from '@/components/ui/progress';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ExternalLink, Copy, Check, AlertTriangle, Shield, ShieldCheck, FileDown } from 'lucide-react';
import { useState } from 'react';
import PlagiarismReport from './PlagiarismReport';

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
  const hasMatches = matches && matches.length > 0;
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  
  // Color based on plagiarism severity
  const getSeverityColor = (percentage: number) => {
    if (percentage < 15) return "bg-green-500";
    if (percentage < 30) return "bg-yellow-500";
    if (percentage < 50) return "bg-orange-500";
    return "bg-red-500";
  };
  
  // Get severity label
  const getSeverityLabel = (percentage: number) => {
    if (percentage < 15) return { text: "Low Similarity", icon: <ShieldCheck className="h-5 w-5 text-green-500" /> };
    if (percentage < 30) return { text: "Moderate Similarity", icon: <Shield className="h-5 w-5 text-yellow-500" /> };
    if (percentage < 50) return { text: "High Similarity", icon: <AlertTriangle className="h-5 w-5 text-orange-500" /> };
    return { text: "Very High Similarity", icon: <AlertTriangle className="h-5 w-5 text-red-500" /> };
  };
  
  // Copy text to clipboard
  const copyToClipboard = (text: string, index: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };
  
  const severityInfo = getSeverityLabel(plagiarismPercentage);
  
  return (
    <div className="space-y-8 animate-fade-in">
      {/* Main Score Card */}
      <Card className="overflow-hidden">
        <div className="relative">
          <div className={`absolute top-0 left-0 h-1 w-full ${getSeverityColor(plagiarismPercentage)}`}></div>
        </div>
        
        <CardHeader className="pb-3">
          <div className="flex justify-between items-start">
            <div>
              <CardTitle className="text-2xl font-bold">Plagiarism Analysis Results</CardTitle>
              <CardDescription>Analysis completed successfully</CardDescription>
            </div>
            <Badge 
              variant={plagiarismPercentage > 30 ? "destructive" : "outline"}
              className="text-sm px-3 py-1.5 font-medium"
            >
              {plagiarismPercentage.toFixed(1)}% Match
            </Badge>
          </div>
        </CardHeader>
        
        <CardContent>
          <div className="flex gap-4 items-center mb-2">
            {severityInfo.icon}
            <div className="flex-1">
              <div className="flex justify-between items-center mb-1">
                <span className="text-sm font-medium">{severityInfo.text}</span>
                <span className="text-xs text-muted-foreground">{plagiarismPercentage.toFixed(1)}%</span>
              </div>
              <Progress 
                value={plagiarismPercentage} 
                className={`h-2 ${getSeverityColor(plagiarismPercentage)}`}
              />
            </div>
          </div>
          
          <p className="text-sm text-muted-foreground mt-4">
            {hasMatches 
              ? `Found ${matches.length} matching source${matches.length !== 1 ? 's' : ''}`
              : "No matching sources detected. Your content appears to be original."
            }
          </p>
          
          {/* Add PDF Report download button */}
          <div className="mt-4 flex justify-end">
            <PlagiarismReport 
              plagiarismPercentage={plagiarismPercentage}
              matches={matches}
              fullTextWithHighlights={fullTextWithHighlights}
            />
          </div>
        </CardContent>
      </Card>

      {/* Tabs for different views */}
      <Tabs defaultValue="sources" className="w-full">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="sources">Matched Sources</TabsTrigger>
          <TabsTrigger value="fulltext">Full Text Analysis</TabsTrigger>
        </TabsList>
        
        <TabsContent value="sources" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Matched Sources</CardTitle>
              <CardDescription>
                {hasMatches 
                  ? "The following sections of text match existing online sources"
                  : "No matching sources were found in our database"
                }
              </CardDescription>
            </CardHeader>
            <CardContent>
              {hasMatches ? (
                <div className="space-y-4">
                  {matches.map((match, index) => (
                    <div key={index} className="p-4 border rounded-lg bg-card hover:bg-accent/5 transition-colors">
                      <div className="flex justify-between items-start gap-4">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <Badge 
                              variant="secondary" 
                              className={`px-2 py-0.5 ${match.similarityScore && match.similarityScore > 0.8 ? 'bg-red-100 text-red-700' : ''}`}
                            >
                              {match.similarityScore ? `${(match.similarityScore * 100).toFixed(0)}%` : 'Match'}
                            </Badge>
                            <span className="text-xs text-muted-foreground truncate">
                              {new URL(match.sourceUrl).hostname.replace('www.', '')}
                            </span>
                          </div>
                          <div className="relative rounded bg-muted/50 p-3 text-sm">
                            <Button 
                              variant="ghost" 
                              size="sm" 
                              className="absolute top-1 right-1 h-6 w-6 p-0 opacity-70 hover:opacity-100"
                              onClick={() => copyToClipboard(match.textSnippet, index)}
                            >
                              {copiedIndex === index ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
                              <span className="sr-only">Copy</span>
                            </Button>
                            {match.textSnippet}
                          </div>
                        </div>
                      </div>
                      <div className="mt-3 flex items-center justify-between">
                        <a 
                          href={match.sourceUrl} 
                          target="_blank" 
                          rel="noopener noreferrer" 
                          className="text-primary text-sm flex items-center gap-1 hover:underline"
                        >
                          View source <ExternalLink className="h-3 w-3" />
                        </a>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <ShieldCheck className="h-16 w-16 text-green-500 mb-4" />
                  <h3 className="text-lg font-medium mb-2">No matching sources found</h3>
                  <p className="text-muted-foreground max-w-md">
                    Your content appears to be original. No significant matches were found in our database of online sources.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="fulltext" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Full Text Analysis</CardTitle>
              <CardDescription>
                Highlighted sections indicate potential matches with other sources
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[500px] rounded-md border">
                <div className="p-4 prose prose-sm max-w-none">
                  <style {...({ jsx: true, global: true } as any)}>{`
                    .highlight {
                      background-color: rgba(255, 200, 0, 0.2);
                      border-bottom: 2px solid orange;
                      padding: 1px 0;
                    }
                  `}</style>
                  <div dangerouslySetInnerHTML={{ __html: fullTextWithHighlights }} />
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default Results;