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
    id: 'gabriel-hansen',
    name: 'Gabriel Hansen',
    role: 'Founder, CEO',
    bio: 'Visionary leader with a passion for 3D technology and real estate innovation.',
    imageSrc: '/assets/gabriel-hansen.png',
    linkedinUrl: 'https://www.linkedin.com/in/gabriel-hansen-8697482ba/',
  },
  {
    id: 'jayden-flake',
    name: 'Jayden Flake',
    role: 'Head of GTM',
    bio: 'Expert in go-to-market strategy and growth.',
    imageSrc: '/assets/jayden-flake.png',
    linkedinUrl: 'https://www.linkedin.com/in/jaydenflake/',
  },
  {
    id: 'samuel-gibby',
    name: 'Samuel Gibby',
    role: 'Growth Lead',
    bio: 'Focused on scaling and growth initiatives.',
    imageSrc: '/assets/samuel-gibby.png',
    linkedinUrl: 'https://www.linkedin.com/in/samuel-gibby/',
  },
];
