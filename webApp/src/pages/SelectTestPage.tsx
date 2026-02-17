import React, { useState } from 'react';
import { Select, SelectItem } from '@/components/ui/Select';

const SelectTestPage: React.FC = () => {
  const [value1, setValue1] = useState<string>('');
  const [value2, setValue2] = useState<string>('');
  const [value3, setValue3] = useState<string>('');

  return (
    <div className="p-8 space-y-8">
      <h1 className="text-2xl font-bold">Select Component Test</h1>

      <div className="space-y-4">
        <h2 className="text-lg font-semibold">Basic Select with Placeholder</h2>
        <Select placeholder="Choose an option" value={value1} onValueChange={setValue1}>
          <SelectItem value="option1">Option 1</SelectItem>
          <SelectItem value="option2">Option 2</SelectItem>
          <SelectItem value="option3">Option 3</SelectItem>
        </Select>
        <p>Selected: {value1 || 'None'}</p>
      </div>

      <div className="space-y-4">
        <h2 className="text-lg font-semibold">Different Sizes</h2>
        <div className="space-y-2">
          <div>
            <label className="block text-sm font-medium mb-1">Size 1</label>
            <Select size="1" placeholder="Size 1" value={value2} onValueChange={setValue2}>
              <SelectItem value="small1">Small Option 1</SelectItem>
              <SelectItem value="small2">Small Option 2</SelectItem>
            </Select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Size 2 (Default)</label>
            <Select size="2" placeholder="Size 2">
              <SelectItem value="medium1">Medium Option 1</SelectItem>
              <SelectItem value="medium2">Medium Option 2</SelectItem>
            </Select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Size 3</label>
            <Select size="3" placeholder="Size 3" value={value3} onValueChange={setValue3}>
              <SelectItem value="large1">Large Option 1</SelectItem>
              <SelectItem value="large2">Large Option 2</SelectItem>
            </Select>
          </div>
        </div>
        <p>Size 2 Selected: {value2 || 'None'}</p>
        <p>Size 3 Selected: {value3 || 'None'}</p>
      </div>

      <div className="space-y-4">
        <h2 className="text-lg font-semibold">Different Variants</h2>
        <div className="space-y-2">
          <Select variant="surface" placeholder="Surface variant">
            <SelectItem value="surf1">Surface 1</SelectItem>
            <SelectItem value="surf2">Surface 2</SelectItem>
          </Select>

          <Select variant="classic" placeholder="Classic variant">
            <SelectItem value="classic1">Classic 1</SelectItem>
            <SelectItem value="classic2">Classic 2</SelectItem>
          </Select>

          <Select variant="soft" placeholder="Soft variant">
            <SelectItem value="soft1">Soft 1</SelectItem>
            <SelectItem value="soft2">Soft 2</SelectItem>
          </Select>

          <Select variant="ghost" placeholder="Ghost variant">
            <SelectItem value="ghost1">Ghost 1</SelectItem>
            <SelectItem value="ghost2">Ghost 2</SelectItem>
          </Select>
        </div>
      </div>

      <div className="space-y-4">
        <h2 className="text-lg font-semibold">With Colors</h2>
        <div className="space-y-2">
          <Select color="indigo" variant="soft" placeholder="Indigo color">
            <SelectItem value="indigo1">Indigo Option 1</SelectItem>
            <SelectItem value="indigo2">Indigo Option 2</SelectItem>
          </Select>

          <Select color="crimson" variant="soft" placeholder="Crimson color">
            <SelectItem value="crimson1">Crimson Option 1</SelectItem>
            <SelectItem value="crimson2">Crimson Option 2</SelectItem>
          </Select>
        </div>
      </div>
    </div>
  );
};

export default SelectTestPage;
