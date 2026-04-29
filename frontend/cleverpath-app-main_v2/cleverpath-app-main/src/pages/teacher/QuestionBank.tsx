import { useEffect, useState } from 'react';
import { Plus, Edit, Trash2, Search, HelpCircle, Settings } from 'lucide-react';
import {
    listQuizzes,
    listQuestions,
    createQuestion,
    updateQuestion,
    deleteQuestion,
    updateQuiz,
    QuizResponse,
    QuestionResponse,
    fetchLessons,
    fetchAdminSubjects,
    Lesson,
    Subject,
} from '@/services/api';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogFooter,
} from '@/components/ui/dialog';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';

const QuestionBank = () => {
    const [subjects, setSubjects] = useState<Subject[]>([]);
    const [lessons, setLessons] = useState<Lesson[]>([]);
    const [quizzes, setQuizzes] = useState<QuizResponse[]>([]);
    const [questions, setQuestions] = useState<QuestionResponse[]>([]);

    const [selectedSubjectId, setSelectedSubjectId] = useState<string>('all');
    const [selectedLessonId, setSelectedLessonId] = useState<string>('all');

    const [loading, setLoading] = useState(true);
    const [isQuestionDialogOpen, setIsQuestionDialogOpen] = useState(false);
    const [isQuizSettingsOpen, setIsQuizSettingsOpen] = useState(false);
    const [editingQuestion, setEditingQuestion] = useState<QuestionResponse | null>(null);
    const [submitting, setSubmitting] = useState(false);

    // Quiz settings form for editing the default quiz
    const [quizSettingsForm, setQuizSettingsForm] = useState({
        title: '',
        description: '',
        default_num_questions: 10,
        passing_score: 70,
        allow_rl_adaptation: true,
    });

    const [formData, setFormData] = useState({
        quiz_id: '',
        question_text: '',
        code_snippet: '',
        options: { A: '', B: '', C: '', D: '' },
        correct_answer: 'A',
        explanation: '',
        difficulty: 0.5,
        concept: '',
        part: 1,
    });

    useEffect(() => {
        loadData();
    }, []);

    // Reset lesson selection when subject changes
    useEffect(() => {
        setSelectedLessonId('all');
    }, [selectedSubjectId]);

    const loadData = async () => {
        try {
            const [subjectsData, lessonsData, quizzesData, questionsData] = await Promise.all([
                fetchAdminSubjects(),
                fetchLessons(),
                listQuizzes(),
                listQuestions(),
            ]);
            setSubjects(subjectsData);
            setLessons(lessonsData);
            setQuizzes(quizzesData);
            setQuestions(questionsData);
        } catch (error) {
            console.error('Failed to load data:', error);
            toast.error('Failed to load data');
        } finally {
            setLoading(false);
        }
    };

    // The "default quiz" for a lesson is the first quiz created for it
    const getDefaultQuizForLesson = (lessonId: string): QuizResponse | undefined => {
        return quizzes
            .filter(q => q.lesson_id === lessonId)
            .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())[0];
    };

    // All default quizzes visible in the current filter scope
    const visibleDefaultQuizIds = (() => {
        const targetLessons = selectedLessonId !== 'all'
            ? lessons.filter(l => l.id === selectedLessonId)
            : availableLessons;
        return targetLessons
            .map(l => getDefaultQuizForLesson(l.id))
            .filter(Boolean)
            .map(q => q!.id);
    });

    const handleOpenQuestionDialog = (question?: QuestionResponse) => {
        // Determine which quiz to pre-select
        let defaultQuizId = '';
        if (selectedLessonId !== 'all') {
            defaultQuizId = getDefaultQuizForLesson(selectedLessonId)?.id || '';
        }

        if (question) {
            setEditingQuestion(question);
            setFormData({
                quiz_id: question.quiz_id,
                question_text: question.question_text,
                code_snippet: question.code_snippet || '',
                options: question.options,
                correct_answer: question.correct_answer,
                explanation: question.explanation || '',
                difficulty: question.difficulty,
                concept: question.concept,
                part: question.part,
            });
        } else {
            setEditingQuestion(null);
            setFormData({
                quiz_id: defaultQuizId,
                question_text: '',
                code_snippet: '',
                options: { A: '', B: '', C: '', D: '' },
                correct_answer: 'A',
                explanation: '',
                difficulty: 0.5,
                concept: '',
                part: 1,
            });
        }
        setIsQuestionDialogOpen(true);
    };

    const handleOpenQuizSettings = () => {
        if (selectedLessonId === 'all') {
            toast.error('Please select a specific lesson to edit its quiz settings');
            return;
        }
        const quiz = getDefaultQuizForLesson(selectedLessonId);
        if (!quiz) {
            toast.error('No quiz found for this lesson');
            return;
        }
        setQuizSettingsForm({
            title: quiz.title,
            description: quiz.description || '',
            default_num_questions: quiz.default_num_questions,
            passing_score: Math.round(quiz.passing_score * 100),
            allow_rl_adaptation: quiz.allow_rl_adaptation,
        });
        setIsQuizSettingsOpen(true);
    };

    const handleSaveQuizSettings = async () => {
        const quiz = getDefaultQuizForLesson(selectedLessonId);
        if (!quiz) return;

        setSubmitting(true);
        try {
            await updateQuiz(quiz.id, {
                title: quizSettingsForm.title,
                description: quizSettingsForm.description || undefined,
                default_num_questions: quizSettingsForm.default_num_questions,
                passing_score: quizSettingsForm.passing_score / 100,
                allow_rl_adaptation: quizSettingsForm.allow_rl_adaptation,
            });
            toast.success('Quiz settings updated!');
            setIsQuizSettingsOpen(false);
            loadData();
        } catch (error: any) {
            toast.error(error.response?.data?.detail || 'Failed to update quiz settings');
        } finally {
            setSubmitting(false);
        }
    };

    const handleSubmitQuestion = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!formData.quiz_id || !formData.question_text || !formData.concept) {
            toast.error('Please fill in all required fields');
            return;
        }
        if (!formData.options.A || !formData.options.B || !formData.options.C || !formData.options.D) {
            toast.error('Please provide all 4 answer options');
            return;
        }

        setSubmitting(true);
        try {
            if (editingQuestion) {
                await updateQuestion(editingQuestion.id, {
                    question_text: formData.question_text,
                    code_snippet: formData.code_snippet || undefined,
                    options: formData.options,
                    correct_answer: formData.correct_answer,
                    explanation: formData.explanation || undefined,
                    difficulty: formData.difficulty,
                    concept: formData.concept,
                });
                toast.success('Question updated successfully!');
            } else {
                await createQuestion({
                    quiz_id: formData.quiz_id,
                    question_text: formData.question_text,
                    code_snippet: formData.code_snippet || undefined,
                    options: formData.options,
                    correct_answer: formData.correct_answer,
                    explanation: formData.explanation || undefined,
                    difficulty: formData.difficulty,
                    concept: formData.concept,
                    part: formData.part,
                });
                toast.success('Question added successfully!');
            }
            setIsQuestionDialogOpen(false);
            loadData();
        } catch (error: any) {
            toast.error(error.response?.data?.detail || 'Failed to save question');
        } finally {
            setSubmitting(false);
        }
    };

    const handleDelete = async (questionId: string) => {
        if (!confirm('Are you sure you want to delete this question?')) return;
        try {
            await deleteQuestion(questionId);
            toast.success('Question deleted!');
            loadData();
        } catch {
            toast.error('Failed to delete question');
        }
    };

    // Filter logic
    const availableLessons = selectedSubjectId === 'all'
        ? lessons
        : lessons.filter(l => l.subject_id === selectedSubjectId);

    const filteredQuestions = questions.filter(q => {
        // Find which lesson this question belongs to
        const quiz = quizzes.find(qz => qz.id === q.quiz_id);
        if (!quiz) return false;

        if (selectedLessonId !== 'all') {
            // Show all questions from any quiz that belongs to the selected lesson
            return quiz.lesson_id === selectedLessonId;
        }
        // Show questions from lessons under the selected subject
        return availableLessons.some(l => l.id === quiz.lesson_id);
    });

    // The default quiz for the currently selected lesson (for displaying its name)
    const activeQuiz = selectedLessonId !== 'all'
        ? getDefaultQuizForLesson(selectedLessonId)
        : undefined;

    if (loading) {
        return (
            <div className="flex min-h-[60vh] items-center justify-center">
                <div className="text-center">
                    <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent mx-auto mb-4"></div>
                    <p className="text-muted-foreground">Loading questions...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between mb-4">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Quiz Generator</h1>
                    <p className="text-muted-foreground mt-1">Manage questions for each lesson's quiz</p>
                </div>
                <div className="flex space-x-3">
                    <Button
                        variant="outline"
                        onClick={handleOpenQuizSettings}
                        disabled={selectedLessonId === 'all'}
                        className="bg-background"
                        title={selectedLessonId === 'all' ? 'Select a lesson first' : 'Edit quiz settings'}
                    >
                        <Settings className="h-4 w-4 mr-2" />
                        Quiz Settings
                    </Button>
                    <Button
                        onClick={() => handleOpenQuestionDialog()}
                        className="bg-primary text-primary-foreground"
                        disabled={selectedLessonId === 'all'}
                        title={selectedLessonId === 'all' ? 'Select a lesson first' : 'Add question'}
                    >
                        <Plus className="h-4 w-4 mr-2" />
                        Add Question
                    </Button>
                </div>
            </div>

            {/* Filters */}
            <Card className="p-4 bg-card border-border mb-6">
                <div className="flex flex-col md:flex-row gap-4">
                    <div className="flex-1">
                        <Label className="text-xs text-muted-foreground mb-1 block">Subject</Label>
                        <Select value={selectedSubjectId} onValueChange={setSelectedSubjectId}>
                            <SelectTrigger className="bg-background">
                                <SelectValue placeholder="All Subjects" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="all">All Subjects</SelectItem>
                                {subjects.map((subject) => (
                                    <SelectItem key={subject.id} value={subject.id}>
                                        {subject.name}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="flex-1">
                        <Label className="text-xs text-muted-foreground mb-1 block">Lesson</Label>
                        <Select value={selectedLessonId} onValueChange={setSelectedLessonId} disabled={selectedSubjectId === 'all'}>
                            <SelectTrigger className="bg-background">
                                <SelectValue placeholder="All Lessons" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="all">All Lessons</SelectItem>
                                {availableLessons.map((lesson) => (
                                    <SelectItem key={lesson.id} value={lesson.id}>
                                        {lesson.title}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                    {/* Active quiz info */}
                    <div className="flex-1 flex flex-col justify-end">
                        {activeQuiz ? (
                            <div className="flex items-center gap-2 h-10">
                                <span className="text-xs text-muted-foreground">Active Quiz:</span>
                                <Badge variant="outline" className="text-primary border-primary/30 bg-primary/5">
                                    {activeQuiz.title}
                                </Badge>
                                <Badge variant="outline" className="text-xs">
                                    {activeQuiz.default_num_questions} Qs
                                </Badge>
                                <Badge variant="outline" className="text-xs">
                                    Pass: {Math.round(activeQuiz.passing_score * 100)}%
                                </Badge>
                            </div>
                        ) : (
                            <div className="h-10 flex items-center">
                                <span className="text-xs text-muted-foreground italic">Select a lesson to see its quiz</span>
                            </div>
                        )}
                    </div>
                </div>
            </Card>

            {/* Questions Table */}
            <Card className="bg-card border-border overflow-hidden">
                {filteredQuestions.length === 0 ? (
                    <div className="text-center py-16 text-muted-foreground">
                        <HelpCircle className="h-12 w-12 mx-auto mb-4 opacity-20" />
                        <p>No questions found for the selected filters.</p>
                        {selectedLessonId !== 'all' && (
                            <Button variant="link" className="mt-2 text-primary" onClick={() => handleOpenQuestionDialog()}>
                                Add the first question
                            </Button>
                        )}
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm text-left">
                            <thead className="text-xs text-muted-foreground uppercase bg-muted/50 border-b border-border">
                                <tr>
                                    <th className="px-6 py-4 font-medium">Question</th>
                                    <th className="px-6 py-4 font-medium">Options (A, B)</th>
                                    <th className="px-6 py-4 font-medium text-center">Difficulty</th>
                                    <th className="px-6 py-4 font-medium text-center">Concept</th>
                                    <th className="px-6 py-4 font-medium text-right">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-border">
                                {filteredQuestions.map((question) => (
                                    <tr key={question.id} className="hover:bg-muted/20 transition-colors">
                                        <td className="px-6 py-4">
                                            <div className="font-medium text-foreground line-clamp-2 max-w-md">
                                                {question.question_text}
                                            </div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="flex flex-col space-y-1 text-xs max-w-xs">
                                                <span className={question.correct_answer === 'A' ? 'font-bold text-success' : 'text-muted-foreground'}>
                                                    (A) {question.options.A}
                                                </span>
                                                <span className={question.correct_answer === 'B' ? 'font-bold text-success' : 'text-muted-foreground'}>
                                                    (B) {question.options.B}
                                                </span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 text-center">
                                            <span className="inline-flex items-center justify-center px-2 py-1 text-xs font-medium rounded-full bg-secondary/10 text-secondary">
                                                {question.difficulty.toFixed(1)}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 text-center text-xs text-muted-foreground">
                                            {question.concept}
                                        </td>
                                        <td className="px-6 py-4 text-right">
                                            <div className="flex items-center justify-end space-x-2">
                                                <Button variant="ghost" size="icon" onClick={() => handleOpenQuestionDialog(question)} className="h-8 w-8 text-muted-foreground hover:text-primary">
                                                    <Edit className="h-4 w-4" />
                                                </Button>
                                                <Button variant="ghost" size="icon" onClick={() => handleDelete(question.id)} className="h-8 w-8 text-muted-foreground hover:text-destructive">
                                                    <Trash2 className="h-4 w-4" />
                                                </Button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </Card>

            {/* Add / Edit Question Dialog */}
            <Dialog open={isQuestionDialogOpen} onOpenChange={setIsQuestionDialogOpen}>
                <DialogContent className="max-w-3xl p-0 overflow-hidden bg-card border-border">
                    <div className="px-6 py-4 border-b border-border bg-muted/30">
                        <DialogTitle className="text-xl">
                            {editingQuestion ? 'Edit Question' : 'Add New Question'}
                        </DialogTitle>
                        {activeQuiz && !editingQuestion && (
                            <p className="text-sm text-muted-foreground mt-1">
                                Adding to: <span className="font-medium text-foreground">{activeQuiz.title}</span>
                            </p>
                        )}
                    </div>

                    <div className="p-6 overflow-y-auto max-h-[70vh] space-y-6">
                        {/* Quiz selector — only shown when no lesson is pre-selected */}
                        {selectedLessonId === 'all' && (
                            <div className="space-y-2">
                                <Label>Target Quiz *</Label>
                                <Select
                                    value={formData.quiz_id}
                                    onValueChange={(value) => setFormData({ ...formData, quiz_id: value })}
                                    disabled={!!editingQuestion}
                                >
                                    <SelectTrigger>
                                        <SelectValue placeholder="Select a quiz" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {quizzes.map((quiz) => (
                                            <SelectItem key={quiz.id} value={quiz.id}>
                                                {quiz.title}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                        )}

                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label>Concept / Topic *</Label>
                                <Input
                                    placeholder="e.g. loops, variables, classes"
                                    value={formData.concept}
                                    onChange={(e) => setFormData({ ...formData, concept: e.target.value })}
                                />
                            </div>
                            <div className="space-y-2">
                                <Label>Part #</Label>
                                <Input
                                    type="number"
                                    min={1}
                                    value={formData.part}
                                    onChange={(e) => setFormData({ ...formData, part: parseInt(e.target.value) || 1 })}
                                />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <Label>Question Stem *</Label>
                            <Textarea
                                placeholder="Write the question here..."
                                value={formData.question_text}
                                onChange={(e) => setFormData({ ...formData, question_text: e.target.value })}
                                className="resize-none h-24"
                            />
                        </div>

                        <div className="space-y-2">
                            <Label>Code Snippet (optional)</Label>
                            <Textarea
                                placeholder="Paste code here if the question refers to a code block..."
                                value={formData.code_snippet}
                                onChange={(e) => setFormData({ ...formData, code_snippet: e.target.value })}
                                className="resize-none h-20 font-mono text-sm"
                            />
                        </div>

                        <div className="space-y-3">
                            <Label>Answer Options</Label>
                            <p className="text-xs text-muted-foreground">Click the radio button to mark the correct answer.</p>
                            <RadioGroup value={formData.correct_answer} onValueChange={(value) => setFormData({ ...formData, correct_answer: value })}>
                                {(['A', 'B', 'C', 'D'] as const).map((key) => (
                                    <div key={key} className={`flex items-center space-x-3 p-3 rounded-lg border ${formData.correct_answer === key ? 'border-primary bg-primary/5' : 'border-border'}`}>
                                        <RadioGroupItem value={key} id={`option-${key}`} />
                                        <div className="font-semibold text-muted-foreground w-6">{key}.</div>
                                        <Input
                                            className="flex-1 border-0 bg-transparent focus-visible:ring-0 px-0"
                                            placeholder={`Option ${key}`}
                                            value={formData.options[key]}
                                            onChange={(e) =>
                                                setFormData({
                                                    ...formData,
                                                    options: { ...formData.options, [key]: e.target.value },
                                                })
                                            }
                                        />
                                    </div>
                                ))}
                            </RadioGroup>
                        </div>

                        <div className="space-y-2">
                            <Label>Explanation</Label>
                            <Textarea
                                placeholder="Explain why the correct answer is right..."
                                value={formData.explanation}
                                onChange={(e) => setFormData({ ...formData, explanation: e.target.value })}
                                className="resize-none h-20"
                            />
                        </div>

                        <div className="space-y-4 pt-2">
                            <div className="flex items-center justify-between">
                                <Label>Difficulty</Label>
                                <span className="font-mono bg-muted px-2 py-1 rounded text-sm">{formData.difficulty.toFixed(1)}</span>
                            </div>
                            <Slider
                                value={[formData.difficulty]}
                                onValueChange={(value) => setFormData({ ...formData, difficulty: value[0] })}
                                min={0} max={1} step={0.1}
                                className="py-2"
                            />
                            <div className="flex justify-between text-xs text-muted-foreground">
                                <span>0.0 (Easy)</span>
                                <span>0.5 (Medium)</span>
                                <span>1.0 (Hard)</span>
                            </div>
                        </div>
                    </div>

                    <div className="px-6 py-4 border-t border-border bg-muted/30 flex justify-end space-x-3">
                        <Button type="button" variant="outline" onClick={() => setIsQuestionDialogOpen(false)}>Cancel</Button>
                        <Button type="button" disabled={submitting} onClick={handleSubmitQuestion} className="bg-primary">
                            {submitting ? 'Saving...' : 'Save Question'}
                        </Button>
                    </div>
                </DialogContent>
            </Dialog>

            {/* Quiz Settings Dialog */}
            <Dialog open={isQuizSettingsOpen} onOpenChange={setIsQuizSettingsOpen}>
                <DialogContent className="sm:max-w-[500px]">
                    <DialogHeader>
                        <DialogTitle>Edit Quiz Settings</DialogTitle>
                        <p className="text-sm text-muted-foreground mt-1">
                            These settings control what students see when they take this quiz.
                        </p>
                    </DialogHeader>
                    <div className="space-y-4 py-4">
                        <div className="space-y-2">
                            <Label>Quiz Title</Label>
                            <Input
                                value={quizSettingsForm.title}
                                onChange={(e) => setQuizSettingsForm({ ...quizSettingsForm, title: e.target.value })}
                            />
                        </div>
                        <div className="space-y-2">
                            <Label>Description</Label>
                            <Textarea
                                rows={2}
                                value={quizSettingsForm.description}
                                onChange={(e) => setQuizSettingsForm({ ...quizSettingsForm, description: e.target.value })}
                                placeholder="Brief description shown to students..."
                                className="resize-none"
                            />
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label>Questions per Session</Label>
                                <Input
                                    type="number"
                                    min={1}
                                    value={quizSettingsForm.default_num_questions}
                                    onChange={(e) => setQuizSettingsForm({ ...quizSettingsForm, default_num_questions: parseInt(e.target.value) || 1 })}
                                />
                                <p className="text-xs text-muted-foreground">How many questions a student answers each quiz attempt</p>
                            </div>
                            <div className="space-y-2">
                                <Label>Passing Score (%)</Label>
                                <Input
                                    type="number"
                                    min={0}
                                    max={100}
                                    value={quizSettingsForm.passing_score}
                                    onChange={(e) => setQuizSettingsForm({ ...quizSettingsForm, passing_score: parseInt(e.target.value) || 70 })}
                                />
                                <p className="text-xs text-muted-foreground">Minimum score to pass this quiz</p>
                            </div>
                        </div>
                        <div className="flex items-center space-x-3 rounded-lg border border-border p-3">
                            <input
                                type="checkbox"
                                id="rl_adaptation"
                                checked={quizSettingsForm.allow_rl_adaptation}
                                onChange={(e) => setQuizSettingsForm({ ...quizSettingsForm, allow_rl_adaptation: e.target.checked })}
                                className="h-4 w-4 accent-primary"
                            />
                            <div>
                                <Label htmlFor="rl_adaptation" className="cursor-pointer">Enable Adaptive Learning (RL)</Label>
                                <p className="text-xs text-muted-foreground">When enabled, the AI adapts question difficulty based on student performance</p>
                            </div>
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setIsQuizSettingsOpen(false)}>Cancel</Button>
                        <Button disabled={submitting} onClick={handleSaveQuizSettings} className="bg-primary">
                            {submitting ? 'Saving...' : 'Save Settings'}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
};

export default QuestionBank;
