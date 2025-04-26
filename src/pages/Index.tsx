
import { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/components/ui/use-toast";
import FileUploader from '@/components/FileUploader';
import TextInput from '@/components/TextInput';
import Results from '@/components/Results';
import { checkPlagiarism, checkStatus, getResults } from '@/api/plagiarismApi';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { Loader } from "lucide-react";

const Index = () => {
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState<string>("initializing");
  const [results, setResults] = useState<any>(null);
  const { toast } = useToast();

  const handleSubmission = async (content: string | File) => {
    setLoading(true);
    setProgress(0);
    setCurrentStep("initializing");
    
    try {
      // Start animation
      setProgress(10);
      setCurrentStep("Initiating plagiarism check...");
      
      const { jobId } = await checkPlagiarism(content);
      
      setProgress(30);
      setCurrentStep("Processing content...");
      
      // Poll for status
      const intervalId = setInterval(async () => {
        setProgress(prev => Math.min(prev + 5, 95)); // Gradually increase progress
        
        const { status } = await checkStatus(jobId);
        
        if (status === "completed") {
          clearInterval(intervalId);
          setProgress(95);
          setCurrentStep("Finalizing report...");
          
          setTimeout(async () => {
            const results = await getResults(jobId);
            setResults(results);
            setLoading(false);
            setProgress(100);
            toast({
              description: "Analysis completed successfully.",
            });
          }, 800); // Small delay for smoother transition
        } else if (status === "failed") {
          clearInterval(intervalId);
          setLoading(false);
          toast({
            title: "Error",
            description: "Failed to process your request. Please try again.",
            variant: "destructive",
          });
        } else {
          // Update step message based on progress
          if (progress > 30 && progress <= 60) {
            setCurrentStep("Analyzing content...");
          } else if (progress > 60) {
            setCurrentStep("Matching against sources...");
          }
        }
      }, 2000);
    } catch (error) {
      setLoading(false);
      toast({
        title: "Error",
        description: "An error occurred. Please try again.",
        variant: "destructive",
      });
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Plagiarism Checker
        </h1>
        <p className="text-gray-600">
          Check your text for plagiarism using our advanced detection tool
        </p>
      </div>

      {!loading && !results && (
        <div className="bg-white rounded-lg shadow-sm border">
          <Tabs defaultValue="text" className="w-full">
            <TabsList className="w-full grid grid-cols-2">
              <TabsTrigger value="text">Check Text</TabsTrigger>
              <TabsTrigger value="file">Upload File</TabsTrigger>
            </TabsList>
            <TabsContent value="text" className="p-6">
              <TextInput onSubmit={handleSubmission} />
            </TabsContent>
            <TabsContent value="file" className="p-6">
              <FileUploader onFileSelect={handleSubmission} />
            </TabsContent>
          </Tabs>
        </div>
      )}

      {loading && (
        <div className="bg-white rounded-lg shadow-sm border p-8 text-center">
          <div className="flex flex-col items-center justify-center gap-6 py-8">
            <div className="relative">
              {/* Circular progress background */}
              <div className="w-24 h-24 rounded-full border-4 border-secondary relative">
                {/* Animated progress circle */}
                <svg className="absolute inset-0 w-24 h-24 transform -rotate-90">
                  <circle 
                    cx="48" 
                    cy="48" 
                    r="40" 
                    fill="transparent"
                    stroke="currentColor" 
                    strokeWidth="8"
                    strokeDasharray={`${2 * Math.PI * 40}`}
                    strokeDashoffset={`${2 * Math.PI * 40 * (1 - progress/100)}`}
                    className="text-primary transition-all duration-300"
                  />
                </svg>
                {/* Spinning loader in center */}
                <div className="absolute inset-0 flex items-center justify-center">
                  <Loader className="w-8 h-8 animate-spin text-primary" />
                </div>
              </div>
            </div>

            <div className="space-y-2 max-w-md mx-auto">
              <Collapsible className="w-full">
                <div className="flex flex-col items-center space-y-2">
                  <h3 className="text-xl font-medium text-gray-900">{currentStep}</h3>
                  <div className="w-full bg-secondary h-2 rounded-full overflow-hidden">
                    <div 
                      className="bg-primary h-full transition-all duration-300 ease-in-out" 
                      style={{ width: `${progress}%` }} 
                    />
                  </div>
                  <span className="text-sm text-muted-foreground">{progress}% complete</span>
                </div>

                <CollapsibleTrigger asChild>
                  <Button variant="link" className="text-sm mt-2">
                    Show details
                  </Button>
                </CollapsibleTrigger>
                
                <CollapsibleContent className="mt-2">
                  <div className="rounded-md bg-secondary/50 p-4 text-sm">
                    <ToggleGroup type="single" defaultValue="content">
                      <ToggleGroupItem value="content">Content Analysis</ToggleGroupItem>
                      <ToggleGroupItem value="sources">Source Matching</ToggleGroupItem>
                      <ToggleGroupItem value="report">Report Generation</ToggleGroupItem>
                    </ToggleGroup>
                    <div className="mt-3 text-left text-muted-foreground">
                      <p>Our AI is analyzing your content for matching phrases and possible plagiarism across our database of academic papers, websites, and published works.</p>
                    </div>
                  </div>
                </CollapsibleContent>
              </Collapsible>
            </div>
          </div>
        </div>
      )}

      {results && (
        <Results
          plagiarismPercentage={results.plagiarismPercentage}
          matches={results.matches}
          fullTextWithHighlights={results.fullTextWithHighlights}
        />
      )}
    </div>
  );
};

export default Index;
