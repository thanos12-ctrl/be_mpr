import { useEffect, useState, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Clock, ArrowRight, BookOpen, Copy, Play, Check } from 'lucide-react';
import { fetchTopicContent, updateLessonProgress, Topic } from '@/services/api';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import ReactMarkdown from 'react-markdown';
import Editor from '@monaco-editor/react';
import { toast } from 'sonner';
import axios from "axios";


const TopicContent = () => {
  const { bundleId } = useParams<{ bundleId: string }>();
  const [topic, setTopic] = useState<Topic | null>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);
  const [output, setOutput] = useState<string[]>([]);
  const [showOutput, setShowOutput] = useState(false);
  const [startTime] = useState(Date.now());
  const editorRef = useRef(null);

  const handleCopy = () => {
    if (topic?.codeExample) {
      navigator.clipboard.writeText(topic.codeExample);
      setCopied(true);
      toast.success('Code copied to clipboard!');
      setTimeout(() => setCopied(false), 2000);
    }
  };


  const handleEditorDidMount = (editor) => {
    editorRef.current = editor;
  };

  const handleRun = async () => {
    const code = editorRef.current.getValue();
    const program = {
      language: "java",
      version: "15.0.2",
      files: [
        {
          name: "Main.java",
          content: code,
        },
      ],
    };

    try {
      const response = await axios.post('https://emkc.org/api/v2/piston/execute', program, {
        headers: {
          'Content-Type': 'application/json',
        },
      });
      setOutput(response.data.run.output.split('\n'));
      setShowOutput(true);
    } catch (error) {
      console.error('Error executing code:', error);
      setOutput(['Error executing code']);
    }
  };

  useEffect(() => {
    const loadTopic = async () => {
      if (bundleId) {
        try {
          const data = await fetchTopicContent(bundleId);
          setTopic(data);
        } catch (error) {
          console.error('Failed to load topic:', error);
          toast.error('Failed to load lesson content');
        } finally {
          setLoading(false);
        }
      }
    };
    loadTopic();

    // Track progress on unmount
    return () => {
      if (bundleId) {
        const timeSpent = Math.floor((Date.now() - startTime) / 1000);
        updateLessonProgress(bundleId, timeSpent, 'completed', false).catch(console.error);
      }
    };
  }, [bundleId, startTime]);


  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading content...</p>
        </div>
      </div>
    );
  }

  if (!topic) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="text-center">
          <p className="text-xl text-muted-foreground">Topic not found</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div className="space-y-4">
        <Link
          to="/browse-subjects"
          className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          ← Back to Subjects
        </Link>

        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <h1 className="text-4xl font-bold tracking-tight">{topic.title}</h1>
            <div className="flex items-center space-x-4 text-sm text-muted-foreground">
              <div className="flex items-center space-x-1">
                <Clock className="h-4 w-4" />
                <span>{topic.estimatedTime} min read</span>
              </div>
              <div className="flex items-center space-x-1">
                <BookOpen className="h-4 w-4" />
                <span>Beginner Friendly</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <Card className="p-8 bg-card border-border shadow-[var(--shadow-card)]">
        <div className="space-y-8">
          {/* Introduction */}
          <div className="space-y-2">
            <h2 className="text-2xl font-semibold">Introduction</h2>
            <p className="text-muted-foreground leading-relaxed">{topic.introduction}</p>
          </div>

          {/* Main Content */}
          <div className="space-y-4">
            <h2 className="text-2xl font-semibold">Overview</h2>
            <div className="prose prose-slate dark:prose-invert max-w-none">
              <ReactMarkdown>{topic.mainContent}</ReactMarkdown>
            </div>
          </div>

          {/* Code Example */}
          <div className="space-y-4">
            <h2 className="text-2xl font-semibold">Code Example</h2>
            <div className="space-y-3">
              <div className="relative rounded-lg overflow-hidden border border-border">
                <div className="absolute top-3 right-3 z-10 flex gap-2">
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={handleCopy}
                    className="h-8"
                  >
                    {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                    {copied ? 'Copied' : 'Copy'}
                  </Button>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={handleRun}
                    className="h-8"
                  >
                    <Play className="h-4 w-4" />
                    Run
                  </Button>
                </div>
                <Editor
                  height="300px"
                  defaultLanguage="java"
                  value={topic.codeExample}
                  theme="vs-dark"
                  onMount={handleEditorDidMount}
                  options={{
                    minimap: { enabled: false },
                    scrollBeyondLastLine: false,
                    fontSize: 14,
                    readOnly: false,
                    lineNumbers: 'on',
                    renderLineHighlight: 'none',
                    padding: { top: 16, bottom: 16 },
                  }}
                />
              </div>

              {showOutput && (
                <div className="rounded-lg border border-border bg-muted/50 p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-semibold">Output</h3>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setShowOutput(false)}
                      className="h-6 text-xs"
                    >
                      Clear
                    </Button>
                  </div>
                  <div className="bg-background rounded-md p-3 font-mono text-sm space-y-1">
                    {output.map((line, index) => (
                      <div key={index} className="text-foreground whitespace-pre-wrap break-words">
                        {line}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
          {/* Key Points */}
          <div className="space-y-4">
            <h2 className="text-2xl font-semibold">Key Takeaways</h2>
            <ul className="space-y-2">
              {topic.keyPoints.map((point, index) => (
                <li key={index} className="flex items-start space-x-3">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary text-sm font-medium">
                    {index + 1}
                  </span>
                  <span className="text-muted-foreground leading-relaxed">{point}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </Card>

      <div className="flex justify-between items-center p-6 rounded-lg bg-gradient-to-r from-primary/10 to-accent/10 border border-primary/20">
        <div>
          <h3 className="text-lg font-semibold mb-1">Ready to test your knowledge?</h3>
          <p className="text-sm text-muted-foreground">
            Take a quiz to check your understanding
          </p>
        </div>
        <Link to={`/quiz/${bundleId}`}>
          <Button size="lg" className="bg-gradient-to-r from-primary to-primary-glow hover:opacity-90 transition-opacity">
            Start Quiz
            <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        </Link>
      </div>
    </div>
  );
};

export default TopicContent;
