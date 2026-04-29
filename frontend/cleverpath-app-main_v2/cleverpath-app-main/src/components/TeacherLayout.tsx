import { Link, useLocation, useNavigate } from 'react-router-dom';
import { BookOpen, Calendar, HelpCircle, Users, Layout, LogOut, Plus, UserCog } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';

const TeacherLayout = ({ children }: { children: React.ReactNode }) => {
    const location = useLocation();
    const navigate = useNavigate();
    const { user, logout } = useAuth();

    const isActive = (path: string) => {
        return location.pathname === path || location.pathname.startsWith(path);
    };

    const handleLogout = () => {
        logout();
        navigate('/');
    };

    const navItems = [
        { name: 'Content Library', path: '/teacher/subjects', icon: BookOpen },
        { name: 'Lesson Planner', path: '/teacher/lessons', icon: Calendar },
        { name: 'Quiz Generator', path: '/teacher/questions', icon: HelpCircle },
        { name: 'Student Progress', path: '/teacher/progress', icon: Users },
    ];

    const teacherName = user?.full_name || 'Teacher';
    const teacherInitials = teacherName.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();

    return (
        <div className="flex h-screen bg-background overflow-hidden">
            {/* Sidebar */}
            <aside className="w-64 border-r border-border bg-card/50 flex flex-col justify-between">
                <div>
                    <div className="p-6">
                        <div className="flex items-center space-x-3 mb-2">
                            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-primary-foreground font-bold text-xl">
                                {teacherInitials}
                            </div>
                            <div className="overflow-hidden">
                                <h2 className="font-bold text-lg leading-tight truncate">{teacherName}</h2>
                                <p className="text-xs text-muted-foreground">CleverPath</p>
                            </div>
                        </div>
                    </div>

                    <nav className="space-y-1 px-4">
                        {navItems.map((item) => (
                            <Link
                                key={item.name}
                                to={item.path}
                                className={`flex items-center space-x-3 rounded-lg px-4 py-3 text-sm font-medium transition-colors ${
                                    isActive(item.path)
                                        ? 'bg-primary/10 text-primary'
                                        : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                                }`}
                            >
                                <item.icon className={`h-5 w-5 ${isActive(item.path) ? 'text-primary' : 'text-muted-foreground'}`} />
                                <span>{item.name}</span>
                            </Link>
                        ))}
                    </nav>
                </div>

                <div className="p-4 space-y-2">
                    <Button 
                        variant="ghost" 
                        className="w-full justify-start text-muted-foreground hover:text-foreground" 
                        onClick={() => toast.info('Edit Profile functionality coming soon')}
                    >
                        <UserCog className="mr-2 h-4 w-4" />
                        Edit Profile
                    </Button>
                    <Button variant="ghost" className="w-full justify-start text-muted-foreground hover:text-foreground" onClick={handleLogout}>
                        <LogOut className="mr-2 h-4 w-4" />
                        Sign Out
                    </Button>
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 overflow-y-auto bg-slate-50/50">
                <div className="container mx-auto p-8 max-w-7xl">
                    {children}
                </div>
            </main>
        </div>
    );
};

export default TeacherLayout;
