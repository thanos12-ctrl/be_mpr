import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Save, Eye } from 'lucide-react';
import { fetchSubjects, createLesson, fetchLessons, Subject, Lesson } from '@/services/api';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import { toast } from 'sonner';
import Editor from '@monaco-editor/react';

const LessonEditor = () => {
    const navigate = useNavigate();
    const [subjects, setSubjects] = useState<Subject[]>([]);
    const [lessons, setLessons] = useState<Lesson[]>([]);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [showForm, setShowForm] = useState(false);

    const [formData, setFormData] = useState({
        subject_id: '',
        lesson_number: 1,
        title: '',
        slug: '',
        introduction: '',
        code_example: '',
        key_takeaways: [''],
        estimated_time_minutes: 15,
        difficulty_level: 3,
    });

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            const [subjectsData, lessonsData] = await Promise.all([
                fetchSubjects(),
                fetchLessons(),
            ]);
            setSubjects(subjectsData);
            setLessons(lessonsData);
        } catch (error) {
            console.error('Failed to load data:', error);
            toast.error('Failed to load data');
        } finally {
            setLoading(false);
        }
    };

    const handleAddTakeaway = () => {
        setFormData({
            ...formData,
            key_takeaways: [...formData.key_takeaways, ''],
        });
    };

    const handleRemoveTakeaway = (index: number) => {
        const newTakeaways = formData.key_takeaways.filter((_, i) => i !== index);
        setFormData({ ...formData, key_takeaways: newTakeaways });
    };

    const handleTakeawayChange = (index: number, value: string) => {
        const newTakeaways = [...formData.key_takeaways];
        newTakeaways[index] = value;
        setFormData({ ...formData, key_takeaways: newTakeaways });
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!formData.subject_id || !formData.title || !formData.introduction) {
            toast.error('Please fill in all required fields');
            return;
        }

        const validTakeaways = formData.key_takeaways.filter((t) => t.trim() !== '');
        if (validTakeaways.length < 3) {
            toast.error('Please add at least 3 key takeaways');
            return;
        }

        setSubmitting(true);
        try {
            await createLesson({
                subject_id: formData.subject_id,
                lesson_number: formData.lesson_number,
                title: formData.title,
                slug: formData.slug || formData.title.toLowerCase().replace(/\s+/g, '-'),
                introduction: formData.introduction,
                code_example: formData.code_example || undefined,
                key_takeaways: validTakeaways,
                estimated_time_minutes: formData.estimated_time_minutes,
                difficulty_level: formData.difficulty_level,
                prerequisites: [],
            });

            toast.success('Lesson created successfully!');
            setShowForm(false);
            setFormData({
                subject_id: '',
                lesson_number: 1,
                title: '',
                slug: '',
                introduction: '',
                code_example: '',
                key_takeaways: [''],
                estimated_time_minutes: 15,
                difficulty_level: 3,
            });
            loadData();
        } catch (error: any) {
            console.error('Failed to create lesson:', error);
            toast.error(error.response?.data?.detail || 'Failed to create lesson');
        } finally {
            setSubmitting(false);
        }
    };

    if (loading) {
        return (
            <div className="flex min-h-[60vh] items-center justify-center">
                <div className="text-center">
                    <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent mx-auto mb-4"></div>
                    <p className="text-muted-foreground">Loading...</p>
                </div>
            </div>
        );
    }

    if (!showForm) {
        return (
            <div className="max-w-6xl mx-auto space-y-8">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-3xl font-bold">Manage Lessons</h1>
                        <p className="text-muted-foreground mt-2">Create and organize your course lessons</p>
                    </div>
                    <Button onClick={() => setShowForm(true)} className="bg-gradient-to-r from-primary to-primary-glow">
                        <Plus className="h-4 w-4 mr-2" />
                        Create Lesson
                    </Button>
                </div>

                {lessons.length === 0 ? (
                    <Card className="p-12 text-center bg-card border-border">
                        <div className="max-w-md mx-auto">
                            <div className="text-6xl mb-4">📝</div>
                            <h3 className="text-xl font-semibold mb-2">No lessons yet</h3>
                            <p className="text-muted-foreground mb-6">
                                Create your first lesson to start building your course content.
                            </p>
                            <Button onClick={() => setShowForm(true)} className="bg-gradient-to-r from-primary to-primary-glow">
                                <Plus className="h-4 w-4 mr-2" />
                                Create Your First Lesson
                            </Button>
                        </div>
                    </Card>
                ) : (
                    <div className="space-y-4">
                        {lessons.map((lesson) => {
                            const subject = subjects.find((s) => s.id === lesson.subject_id);
                            return (
                                <Card key={lesson.id} className="p-6 bg-card border-border hover:shadow-[var(--shadow-elevated)] transition-all">
                                    <div className="flex items-start justify-between">
                                        <div className="flex-1">
                                            <div className="flex items-center space-x-3 mb-2">
                                                <span className="text-sm font-medium text-muted-foreground">
                                                    Lesson {lesson.lesson_number}
                                                </span>
                                                {subject && (
                                                    <span className="text-sm text-muted-foreground">
                                                        {subject.icon} {subject.name}
                                                    </span>
                                                )}
                                            </div>
                                            <h3 className="text-lg font-semibold mb-1">{lesson.title}</h3>
                                            <p className="text-sm text-muted-foreground line-clamp-2">{lesson.introduction}</p>
                                            <div className="flex items-center space-x-4 mt-3 text-xs text-muted-foreground">
                                                <span>⏱️ {lesson.estimated_time_minutes} min</span>
                                                <span>📊 Level {lesson.difficulty_level}/5</span>
                                                <span className={lesson.is_published ? 'text-success' : ''}>
                                                    {lesson.is_published ? '● Published' : '○ Draft'}
                                                </span>
                                            </div>
                                        </div>
                                        <Button variant="outline" size="sm">
                                            <Eye className="h-4 w-4 mr-1" />
                                            View
                                        </Button>
                                    </div>
                                </Card>
                            );
                        })}
                    </div>
                )}
            </div>
        );
    }

    return (
        <div className="max-w-4xl mx-auto space-y-8">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold">Create Lesson</h1>
                    <p className="text-muted-foreground mt-2">Add a new lesson to your course</p>
                </div>
                <Button variant="outline" onClick={() => setShowForm(false)}>
                    Cancel
                </Button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
                <Card className="p-6 bg-card border-border">
                    <h2 className="text-xl font-semibold mb-4">Basic Information</h2>

                    <div className="space-y-4">
                        <div className="space-y-2">
                            <Label htmlFor="subject">Subject *</Label>
                            <Select value={formData.subject_id} onValueChange={(value) => setFormData({ ...formData, subject_id: value })}>
                                <SelectTrigger>
                                    <SelectValue placeholder="Select a subject" />
                                </SelectTrigger>
                                <SelectContent>
                                    {subjects.map((subject) => (
                                        <SelectItem key={subject.id} value={subject.id}>
                                            {subject.icon} {subject.name}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label htmlFor="lesson_number">Lesson Number *</Label>
                                <Input
                                    id="lesson_number"
                                    type="number"
                                    min="1"
                                    value={formData.lesson_number}
                                    onChange={(e) => setFormData({ ...formData, lesson_number: parseInt(e.target.value) })}
                                    required
                                />
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="estimated_time">Estimated Time (minutes) *</Label>
                                <Input
                                    id="estimated_time"
                                    type="number"
                                    min="5"
                                    max="120"
                                    value={formData.estimated_time_minutes}
                                    onChange={(e) => setFormData({ ...formData, estimated_time_minutes: parseInt(e.target.value) })}
                                    required
                                />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="title">Lesson Title *</Label>
                            <Input
                                id="title"
                                placeholder="e.g., Introduction to Variables"
                                value={formData.title}
                                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                                required
                            />
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="slug">URL Slug (optional)</Label>
                            <Input
                                id="slug"
                                placeholder="Auto-generated from title if left empty"
                                value={formData.slug}
                                onChange={(e) => setFormData({ ...formData, slug: e.target.value })}
                            />
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="difficulty">Difficulty Level: {formData.difficulty_level}/5</Label>
                            <Slider
                                value={[formData.difficulty_level]}
                                onValueChange={(value) => setFormData({ ...formData, difficulty_level: value[0] })}
                                min={1}
                                max={5}
                                step={1}
                                className="mt-2"
                            />
                            <div className="flex justify-between text-xs text-muted-foreground">
                                <span>Beginner</span>
                                <span>Intermediate</span>
                                <span>Advanced</span>
                            </div>
                        </div>
                    </div>
                </Card>

                <Card className="p-6 bg-card border-border">
                    <h2 className="text-xl font-semibold mb-4">Content</h2>

                    <div className="space-y-4">
                        <div className="space-y-2">
                            <Label htmlFor="introduction">Introduction *</Label>
                            <Textarea
                                id="introduction"
                                placeholder="Explain what students will learn in this lesson..."
                                value={formData.introduction}
                                onChange={(e) => setFormData({ ...formData, introduction: e.target.value })}
                                rows={5}
                                required
                            />
                        </div>

                        <div className="space-y-2">
                            <Label>Code Example (optional)</Label>
                            <div className="border border-border rounded-lg overflow-hidden">
                                <Editor
                                    height="300px"
                                    defaultLanguage="java"
                                    value={formData.code_example}
                                    onChange={(value) => setFormData({ ...formData, code_example: value || '' })}
                                    theme="vs-dark"
                                    options={{
                                        minimap: { enabled: false },
                                        fontSize: 14,
                                    }}
                                />
                            </div>
                        </div>
                    </div>
                </Card>

                <Card className="p-6 bg-card border-border">
                    <h2 className="text-xl font-semibold mb-4">Key Takeaways (min 3) *</h2>

                    <div className="space-y-3">
                        {formData.key_takeaways.map((takeaway, index) => (
                            <div key={index} className="flex items-center space-x-2">
                                <Input
                                    placeholder={`Takeaway ${index + 1}`}
                                    value={takeaway}
                                    onChange={(e) => handleTakeawayChange(index, e.target.value)}
                                />
                                {formData.key_takeaways.length > 1 && (
                                    <Button
                                        type="button"
                                        variant="outline"
                                        size="sm"
                                        onClick={() => handleRemoveTakeaway(index)}
                                    >
                                        Remove
                                    </Button>
                                )}
                            </div>
                        ))}
                        <Button type="button" variant="outline" onClick={handleAddTakeaway} className="w-full">
                            <Plus className="h-4 w-4 mr-2" />
                            Add Takeaway
                        </Button>
                    </div>
                </Card>

                <div className="flex justify-end space-x-4">
                    <Button type="button" variant="outline" onClick={() => setShowForm(false)}>
                        Cancel
                    </Button>
                    <Button type="submit" disabled={submitting} className="bg-gradient-to-r from-primary to-primary-glow">
                        <Save className="h-4 w-4 mr-2" />
                        {submitting ? 'Creating...' : 'Create Lesson'}
                    </Button>
                </div>
            </form>
        </div>
    );
};

export default LessonEditor;
