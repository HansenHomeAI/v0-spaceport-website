export interface Property {
  id: string;
  title: string;
  location: string;
  imageSrc: string;
  link: string;
}

export interface TeamMember {
  id: string;
  name: string;
  role: string;
  bio: string;
  imageSrc: string; // Using placeholder or generic avatar
  linkedinUrl: string;
}

export const PROPERTIES: Property[] = [
  {
    id: 'deer-knoll',
    title: 'Deer Knoll',
    location: 'Utah',
    imageSrc: '/assets/SpaceportIcons/SpcprtLarge.png', // Placeholder
    link: 'https://hansenhomeai.github.io/WebbyDeerKnoll/',
  },
  {
    id: 'forest-creek',
    title: 'Forest Creek',
    location: 'Utah',
    imageSrc: '/assets/SpaceportIcons/SpcprtLarge.png', // Placeholder
    link: 'https://spcprt.com/spaces/forest-creek-nux',
  },
  {
    id: 'edgewood-farm',
    title: 'Edgewood Farm',
    location: 'Virginia',
    imageSrc: '/assets/SpaceportIcons/SpcprtLarge.png', // Placeholder
    link: 'https://spcprt.com/spaces/edgewood-farm-nux',
  },
  {
    id: 'cromwell-island',
    title: 'Cromwell Island',
    location: 'Montana',
    imageSrc: '/assets/SpaceportIcons/SpcprtLarge.png', // Placeholder
    link: 'https://spcprt.com/spaces/cromwell-island-nux',
  },
];

export const TEAM_MEMBERS: TeamMember[] = [
  {
    id: 'member-1',
    name: 'Team Member 1',
    role: 'Co-Founder & CEO',
    bio: 'Visionary leader with a passion for 3D technology and real estate innovation.',
    imageSrc: '/assets/SpaceportIcons/SpcprtBWIcon.png', // Placeholder
    linkedinUrl: 'https://linkedin.com',
  },
  {
    id: 'member-2',
    name: 'Team Member 2',
    role: 'CTO',
    bio: 'Expert in machine learning and computer vision, driving the core technology.',
    imageSrc: '/assets/SpaceportIcons/SpcprtBWIcon.png', // Placeholder
    linkedinUrl: 'https://linkedin.com',
  },
  {
    id: 'member-3',
    name: 'Team Member 3',
    role: 'Head of Product',
    bio: 'Focused on delivering the best user experience for property tours.',
    imageSrc: '/assets/SpaceportIcons/SpcprtBWIcon.png', // Placeholder
    linkedinUrl: 'https://linkedin.com',
  },
];
