import { useEffect, useState } from 'react';
import { Plus, Edit, Trash2, Search, Clock, CheckCircle, FileText, ChevronRight, X } from 'lucide-react';
import { fetchAdminSubjects, createLesson, fetchLessons, updateLesson, deleteLesson, Subject, Lesson } from '@/services/api';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogFooter,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import Editor from '@monaco-editor/react';
import { toast } from 'sonner';

interface FormData {
    lesson_number: number;
    title: string;
    introduction: string; // short overview/description shown on lesson card
    content: string;      // detailed content / body of lesson
    code_example: string;
    key_takeaways: string; // comma-separated input, split on save
    estimated_time_minutes: number;
    difficulty_level: number;
}

const defaultForm = (): FormData => ({
    lesson_number: 1,
    title: '',
    introduction: '',
    content: '',
    code_example: '',
    key_takeaways: '',
    estimated_time_minutes: 15,
    difficulty_level: 3,
});

const LessonEditor = () => {
    const [subjects, setSubjects] = useState<Subject[]>([]);
    const [lessons, setLessons] = useState<Lesson[]>([]);
    const [selectedSubjectId, setSelectedSubjectId] = useState<string>('');
    const [searchQuery, setSearchQuery] = useState('');
    const [loading, setLoading] = useState(true);

    const [isModalOpen, setIsModalOpen] = useState(false);
    const [editingLesson, setEditingLesson] = useState<Lesson | null>(null);
    const [submitting, setSubmitting] = useState(false);
    const [formData, setFormData] = useState<FormData>(defaultForm());

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            const [subjectsData, lessonsData] = await Promise.all([
                fetchAdminSubjects(),
                fetchLessons(),
            ]);
            setSubjects(subjectsData);
            setLessons(lessonsData);
            if (subjectsData.length > 0 && !selectedSubjectId) {
                setSelectedSubjectId(subjectsData[0].id);
            }
        } catch (error) {
            console.error('Failed to load data:', error);
            toast.error('Failed to load data');
        } finally {
            setLoading(false);
        }
    };

    const handleOpenCreateModal = () => {
        const nextLessonNumber = filteredLessons.length + 1;
        setEditingLesson(null);
        setFormData({ ...defaultForm(), lesson_number: nextLessonNumber });
        setIsModalOpen(true);
    };

    const handleOpenEditModal = (lesson: Lesson) => {
        setEditingLesson(lesson);
        // The backend stores `introduction` as the full body text.
        // We split it: anything before the first blank line is the overview,
        // anything after is the detailed content.
        const lines = (lesson.introduction || '').split('\n\n');
        const overview = lines[0] || '';
        const body = lines.slice(1).join('\n\n');

        setFormData({
            lesson_number: lesson.lesson_number,
            title: lesson.title,
            introduction: overview,
            content: body,
            code_example: lesson.code_example || '',
            key_takeaways: (lesson.key_takeaways || []).join(', '),
            estimated_time_minutes: lesson.estimated_time_minutes,
            difficulty_level: lesson.difficulty_level,
        });
        setIsModalOpen(true);
    };

    const handleDelete = async (lessonId: string) => {
        if (!window.confirm('Are you sure you want to delete this lesson?')) return;
        try {
            await deleteLesson(lessonId);
            toast.success('Lesson deleted');
            loadData();
        } catch (error: any) {
            toast.error(error.response?.data?.detail || 'Failed to delete lesson');
        }
    };

    const buildPayload = () => {
        // Combine overview + detailed content back into the `introduction` field
        const combinedIntroduction = [formData.introduction.trim(), formData.content.trim()]
            .filter(Boolean)
            .join('\n\n');

        const takeaways = formData.key_takeaways
            .split(',')
            .map(t => t.trim())
            .filter(Boolean);

        return {
            subject_id: selectedSubjectId,
            lesson_number: formData.lesson_number,
            title: formData.title,
            slug: formData.title.toLowerCase().replace(/\s+/g, '-'),
            introduction: combinedIntroduction,
            code_example: formData.code_example || undefined,
            key_takeaways: takeaways.length ? takeaways : ['Key concept from this lesson'],
            estimated_time_minutes: formData.estimated_time_minutes,
            difficulty_level: formData.difficulty_level,
            prerequisites: [],
        };
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!selectedSubjectId || !formData.title || !formData.introduction) {
            toast.error('Title and Overview are required');
            return;
        }

        setSubmitting(true);
        try {
            const payload = buildPayload();
            if (editingLesson) {
                await updateLesson(editingLesson.id, payload);
                toast.success('Lesson updated successfully!');
            } else {
                await createLesson(payload);
                toast.success('Lesson created successfully!');
            }
            setIsModalOpen(false);
            loadData();
        } catch (error: any) {
            console.error('Failed to save lesson:', error);
            toast.error(error.response?.data?.detail || 'Failed to save lesson');
        } finally {
            setSubmitting(false);
        }
    };

    const filteredLessons = lessons
        .filter(l =>
            l.subject_id === selectedSubjectId &&
            l.title.toLowerCase().includes(searchQuery.toLowerCase())
        )
        .sort((a, b) => a.lesson_number - b.lesson_number);

    const selectedSubject = subjects.find(s => s.id === selectedSubjectId);

    if (loading) {
        return (
            <div className="flex min-h-[60vh] items-center justify-center">
                <div className="text-center">
                    <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent mx-auto mb-4"></div>
                    <p className="text-muted-foreground">Loading lessons...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center text-muted-foreground text-sm mb-2">
                <span>My Published Subjects</span>
                <ChevronRight className="h-4 w-4 mx-1" />
                <span className="font-semibold text-foreground">
                    {selectedSubject ? selectedSubject.name : 'Select a Subject'}
                </span>
            </div>

            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="flex-1 max-w-md flex items-center space-x-4">
                    <Select value={selectedSubjectId} onValueChange={setSelectedSubjectId}>
                        <SelectTrigger className="w-[250px] bg-card">
                            <SelectValue placeholder="Select Subject" />
                        </SelectTrigger>
                        <SelectContent>
                            {subjects.map(subject => (
                                <SelectItem key={subject.id} value={subject.id}>
                                    {subject.icon} {subject.name}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>
                <Button onClick={handleOpenCreateModal} className="bg-primary text-primary-foreground" disabled={!selectedSubjectId}>
                    <Plus className="h-4 w-4 mr-2" />
                    Create New Lesson
                </Button>
            </div>

            <Card className="p-6 bg-card border-border">
                <div className="flex items-center justify-between mb-6">
                    <h2 className="text-xl font-semibold">Manage Lessons</h2>
                    <div className="relative w-64">
                        <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                        <Input
                            placeholder="Search lessons..."
                            className="pl-8 bg-background"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                        />
                    </div>
                </div>

                {!selectedSubjectId ? (
                    <div className="text-center py-12 text-muted-foreground">
                        <FileText className="h-12 w-12 mx-auto mb-4 opacity-20" />
                        <p>Please select a subject to view its lessons.</p>
                    </div>
                ) : filteredLessons.length === 0 ? (
                    <div className="text-center py-12 text-muted-foreground">
                        <FileText className="h-12 w-12 mx-auto mb-4 opacity-20" />
                        <p>No lessons found. Click "Create New Lesson" to get started.</p>
                    </div>
                ) : (
                    <div className="space-y-3">
                        {filteredLessons.map((lesson) => (
                            <div key={lesson.id} className="flex items-center justify-between p-4 rounded-lg border border-border bg-background hover:border-primary/50 transition-colors">
                                <div className="flex items-start space-x-4">
                                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary font-bold">
                                        {lesson.lesson_number}
                                    </div>
                                    <div>
                                        <h3 className="font-semibold">{lesson.title}</h3>
                                        <p className="text-sm text-muted-foreground line-clamp-1">
                                            {(lesson.introduction || '').split('\n\n')[0]}
                                        </p>
                                        <div className="flex items-center space-x-4 mt-2 text-xs text-muted-foreground">
                                            <span className="flex items-center"><Clock className="h-3 w-3 mr-1" /> {lesson.estimated_time_minutes} mins</span>
                                            <span className="flex items-center"><CheckCircle className="h-3 w-3 mr-1 text-success" /> {lesson.is_published ? 'Published' : 'Draft'}</span>
                                            {lesson.key_takeaways?.length > 0 && (
                                                <span>{lesson.key_takeaways.length} takeaway{lesson.key_takeaways.length !== 1 ? 's' : ''}</span>
                                            )}
                                        </div>
                                    </div>
                                </div>
                                <div className="flex items-center space-x-2 shrink-0">
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        className="bg-primary/5 text-primary hover:bg-primary/10 border-primary/20"
                                        onClick={() => handleOpenEditModal(lesson)}
                                    >
                                        <Edit className="h-4 w-4 mr-2" />
                                        Edit
                                    </Button>
                                    <Button
                                        variant="outline"
                                        size="icon"
                                        className="text-destructive hover:bg-destructive/10 border-destructive/20 hover:text-destructive"
                                        onClick={() => handleDelete(lesson.id)}
                                    >
                                        <Trash2 className="h-4 w-4" />
                                    </Button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </Card>

            <Card className="p-6 bg-gradient-to-br from-primary/10 to-accent/10 border-primary/20">
                <div className="flex items-start space-x-4">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/20">
                        <span className="text-xl">✨</span>
                    </div>
                    <div>
                        <h3 className="font-semibold text-primary mb-1">AI Curriculum Insight</h3>
                        <p className="text-sm text-muted-foreground leading-relaxed">
                            Based on student performance in <span className="font-medium text-foreground">{selectedSubject?.name || 'this subject'}</span>, consider adding more interactive code exercises. Students are completing theoretical lessons 30% faster but spending more time on syntax errors in practical challenges.
                        </p>
                    </div>
                </div>
            </Card>

            {/* Lesson Create / Edit Modal */}
            <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
                <DialogContent className="max-w-5xl h-[90vh] flex flex-col p-0 overflow-hidden">
                    <div className="px-6 py-4 border-b border-border flex justify-between items-center bg-card shrink-0">
                        <DialogTitle className="text-xl">
                            {editingLesson ? `Edit Lesson: ${editingLesson.title}` : 'Create New Lesson'}
                        </DialogTitle>
                    </div>

                    <div className="flex-1 overflow-y-auto p-6 bg-background">
                        <form onSubmit={handleSubmit} className="space-y-6">
                            {/* Row 1: Title + Time */}
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                                <div className="md:col-span-2 space-y-2">
                                    <Label>Lesson Title <span className="text-destructive">*</span></Label>
                                    <Input
                                        placeholder="e.g. Introduction to Variables"
                                        value={formData.title}
                                        onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label>Est. Time (mins)</Label>
                                    <Input
                                        type="number"
                                        min={1}
                                        value={formData.estimated_time_minutes}
                                        onChange={(e) => setFormData({ ...formData, estimated_time_minutes: parseInt(e.target.value) || 15 })}
                                    />
                                </div>
                            </div>

                            {/* Row 2: Overview (short) + Key Takeaways */}
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div className="space-y-2">
                                    <Label>
                                        Overview <span className="text-destructive">*</span>
                                        <span className="text-xs text-muted-foreground ml-2">— Short description shown on lesson card</span>
                                    </Label>
                                    <Textarea
                                        rows={3}
                                        placeholder="A brief summary of what this lesson covers..."
                                        value={formData.introduction}
                                        onChange={(e) => setFormData({ ...formData, introduction: e.target.value })}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label>
                                        Key Takeaways
                                        <span className="text-xs text-muted-foreground ml-2">— Comma-separated</span>
                                    </Label>
                                    <Textarea
                                        rows={3}
                                        placeholder="e.g. Understand variables, Learn data types, Write first program"
                                        value={formData.key_takeaways}
                                        onChange={(e) => setFormData({ ...formData, key_takeaways: e.target.value })}
                                    />
                                </div>
                            </div>

                            {/* Row 3: Lesson Body + Code Example (split editor) */}
                            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6" style={{ height: '380px' }}>
                                {/* Left: Detailed Content */}
                                <div className="flex flex-col border border-border rounded-lg overflow-hidden bg-card">
                                    <div className="px-4 py-2 bg-muted border-b border-border flex items-center">
                                        <span className="text-sm font-medium">Lesson Content</span>
                                        <span className="text-xs text-muted-foreground ml-2">— Detailed body / explanation</span>
                                    </div>
                                    <Textarea
                                        className="flex-1 border-0 rounded-none focus-visible:ring-0 resize-none p-4 h-full"
                                        placeholder="Write the full lesson content here. Supports markdown..."
                                        value={formData.content}
                                        onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                                    />
                                </div>

                                {/* Right: Code Editor */}
                                <div className="flex flex-col border border-border rounded-lg overflow-hidden bg-[#1e1e1e]">
                                    <div className="px-4 py-2 bg-[#2d2d2d] border-b border-[#404040] flex items-center justify-between text-gray-300 shrink-0">
                                        <span className="text-sm font-medium">Code Example</span>
                                        <Badge variant="outline" className="bg-[#1e1e1e] border-[#404040] text-gray-300">Monaco Editor</Badge>
                                    </div>
                                    <div className="flex-1">
                                        <Editor
                                            height="100%"
                                            defaultLanguage="python"
                                            theme="vs-dark"
                                            value={formData.code_example}
                                            onChange={(value) => setFormData({ ...formData, code_example: value || '' })}
                                            options={{
                                                minimap: { enabled: false },
                                                fontSize: 14,
                                                padding: { top: 16 }
                                            }}
                                        />
                                    </div>
                                </div>
                            </div>
                        </form>
                    </div>

                    <div className="px-6 py-4 border-t border-border bg-card flex justify-end space-x-3 shrink-0">
                        <Button variant="outline" onClick={() => setIsModalOpen(false)}>
                            Cancel
                        </Button>
                        <Button onClick={handleSubmit} disabled={submitting} className="bg-primary">
                            {submitting ? 'Saving...' : editingLesson ? 'Update Lesson' : 'Create Lesson'}
                        </Button>
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    );
};

export default LessonEditor;
