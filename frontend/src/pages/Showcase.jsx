import React from 'react';
import { Button } from '../components/ui/Button';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { DataTable } from '../components/ui/DataTable';
import { Sparkline } from '../components/ui/Sparkline';
import { EmptyState } from '../components/ui/EmptyState';
import { LoadingIndicator } from '../components/ui/LoadingIndicator';
import { NavSidebar } from '../components/ui/NavSidebar';
import { useToast } from '../components/ui/Toast';
import { LayoutDashboard, Users, MessageSquare } from 'lucide-react';

const Showcase = () => {
  const { toast } = useToast();

  const handleToastSuccess = () => toast({ message: 'Changes saved', type: 'success' });
  const handleToastError = () => toast({ message: 'This file is larger than 25MB — try a shorter recording.', type: 'error' });

  const navItems = [
    { label: 'Dashboard', icon: LayoutDashboard, href: '/showcase' },
    { label: 'Deals', icon: Users, href: '/showcase-dummy-1' },
    { label: 'WhatsApp', icon: MessageSquare, href: '/showcase-dummy-2' },
  ];

  const tableColumns = [
    { header: 'Deal Name', accessorKey: 'name' },
    { header: 'Value', accessorKey: 'value', isNumeric: true },
    { header: 'Stage', accessorKey: 'stage', cell: (row) => <Badge variant={row.stage}>{row.stage.replace('_', ' ')}</Badge> },
    { header: 'Trend', accessorKey: 'trend', cell: (row) => <Sparkline data={row.trend} width={50} height={20} /> },
  ];

  const tableData = [
    { name: 'Acme Corp Enterprise', value: '₹4,500,000', stage: 'negotiation', trend: [10,20,30,20,40,60] },
    { name: 'Globex Inc Pilot', value: '₹850,000', stage: 'prospecting', trend: [50,40,30,20,10,5] },
    { name: 'Stark Ind Renewal', value: '₹12,000,000', stage: 'closed_won', trend: [10,10,20,40,80,100] },
  ];

  return (
    <div className="min-h-screen bg-bg p-8 flex gap-8">
      <aside className="w-64 flex-shrink-0">
        <div className="bg-surface border border-border rounded-xl p-4 sticky top-8">
          <h2 className="font-display font-semibold text-lg mb-4 px-2 text-ink">LAKSHYA AI</h2>
          <NavSidebar items={navItems} />
        </div>
      </aside>

      <main className="flex-1 max-w-5xl space-y-8">
        <div className="mb-12">
          <h1 className="font-display text-4xl font-semibold mb-2 text-ink">UI Component Showcase</h1>
          <p className="text-gray-500">Design System applied to core components.</p>
        </div>

        {/* Buttons */}
        <Card>
          <CardHeader>
            <CardTitle>Buttons</CardTitle>
          </CardHeader>
          <CardContent className="flex gap-4 items-center">
            <Button variant="primary">Primary Action</Button>
            <Button variant="secondary">Secondary Action</Button>
            <Button variant="ghost">Ghost Action</Button>
            <Button variant="destructive">Destructive</Button>
          </CardContent>
        </Card>

        {/* Badges */}
        <Card>
          <CardHeader>
            <CardTitle>Stage Badges</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-3">
            <Badge variant="prospecting">Prospecting</Badge>
            <Badge variant="demo">Demo</Badge>
            <Badge variant="proposal">Proposal</Badge>
            <Badge variant="negotiation">Negotiation</Badge>
            <Badge variant="closed_won">Closed Won</Badge>
            <Badge variant="closed_lost">Closed Lost</Badge>
            <Badge variant="risk">Risk Flag</Badge>
          </CardContent>
        </Card>

        {/* Data Table */}
        <Card>
          <CardHeader>
            <CardTitle>Data Table</CardTitle>
          </CardHeader>
          <CardContent>
            <DataTable columns={tableColumns} data={tableData} />
          </CardContent>
        </Card>

        {/* Cards & Sparklines */}
        <div className="grid grid-cols-2 gap-6">
          <Card interactive>
            <CardContent>
              <div className="flex justify-between items-start mb-4">
                <div>
                  <p className="text-sm text-gray-500 mb-1">Pipeline Momentum</p>
                  <p className="text-2xl font-display font-semibold text-ink">Strong</p>
                </div>
                <Sparkline data={[10, 20, 15, 30, 45, 60]} color="var(--color-growth)" />
              </div>
            </CardContent>
          </Card>
          <Card interactive>
            <CardContent>
              <div className="flex justify-between items-start mb-4">
                <div>
                  <p className="text-sm text-gray-500 mb-1">At-Risk Revenue</p>
                  <p className="text-2xl font-mono text-ink">₹1,200,000</p>
                </div>
                <Sparkline data={[60, 45, 30, 25, 10, 5]} color="var(--color-risk)" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Toast Triggers */}
        <Card>
          <CardHeader>
            <CardTitle>Toasts & Notifications</CardTitle>
          </CardHeader>
          <CardContent className="flex gap-4">
            <Button onClick={handleToastSuccess}>Trigger Success</Button>
            <Button variant="destructive" onClick={handleToastError}>Trigger Error</Button>
          </CardContent>
        </Card>

        {/* Loading & Empty States */}
        <div className="grid grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Loading Indicator</CardTitle>
            </CardHeader>
            <CardContent>
              <LoadingIndicator message="Analyzing conversation..." />
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Empty State</CardTitle>
            </CardHeader>
            <CardContent>
              <EmptyState message="No deals yet — add your first deal to get started." />
            </CardContent>
          </Card>
        </div>

      </main>
    </div>
  );
};

export default Showcase;
