/**
 * Feed Store
 *
 * Manages feed state for home page and discovery.
 */

import { create } from 'zustand';
import { api, Video, FeedItem, PaginatedResponse } from '../lib/api-client';

// =============================================================================
// MOCK DATA
// =============================================================================

const createMockCreator = (id: string, username: string, display_name: string, seed: string, is_verified: boolean) => ({
  id,
  email: `${username}@mock.scenemachine.io`,
  username,
  display_name,
  avatar_url: `https://api.dicebear.com/7.x/avataaars/svg?seed=${seed}`,
  banner_url: null,
  bio: `Creator profile for ${display_name}`,
  is_verified,
  is_creator: true,
  follower_count: Math.floor(Math.random() * 100000),
  following_count: Math.floor(Math.random() * 500),
  created_at: new Date(Date.now() - Math.random() * 365 * 24 * 60 * 60 * 1000).toISOString(),
});

const MOCK_CREATORS = [
  createMockCreator('c1', 'indie_lens', 'Indie Lens Studios', 'indie_lens', true),
  createMockCreator('c2', 'midnight_cinema', 'Midnight Cinema', 'midnight', true),
  createMockCreator('c3', 'nova_films', 'Nova Films', 'nova', false),
  createMockCreator('c4', 'dream_sequences', 'Dream Sequences', 'dream', true),
  createMockCreator('c5', 'pixel_stories', 'Pixel Stories', 'pixel', false),
  createMockCreator('c6', 'crimson_gate', 'Crimson Gate Productions', 'crimson', true),
];

const MOCK_VIDEOS: Video[] = [
  {
    id: 'v1',
    creator_id: 'c1',
    title: 'The Last Sunset',
    description: 'A contemplative short film about finding peace in life\'s final moments.',
    thumbnail_url: 'https://picsum.photos/seed/sunset/640/360',
    duration_seconds: 1080,
    content_type: 'SHORT',
    monetization_type: 'FREE_AD',
    ticket_price: null,
    creator: MOCK_CREATORS[0],
    view_count: 45200,
    like_count: 3420,
    comment_count: 234,
    published_at: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
    created_at: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString(),
    status: 'PUBLISHED',
    tags: ['drama', 'short film', 'contemplative'],
    quality_score: 92,
    made_with_studio: true,
  },
  {
    id: 'v2',
    creator_id: 'c2',
    title: 'Echoes in the Dark',
    description: 'When a radio operator receives a distress signal from 1943, she must unravel a 80-year-old mystery.',
    thumbnail_url: 'https://picsum.photos/seed/echoes/640/360',
    duration_seconds: 5400,
    content_type: 'FILM',
    monetization_type: 'PAID',
    ticket_price: 4.99,
    creator: MOCK_CREATORS[1],
    view_count: 128500,
    like_count: 9870,
    comment_count: 1243,
    published_at: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
    created_at: new Date(Date.now() - 15 * 24 * 60 * 60 * 1000).toISOString(),
    status: 'PUBLISHED',
    tags: ['thriller', 'mystery', 'historical'],
    quality_score: 96,
    made_with_studio: true,
  },
  {
    id: 'v3',
    creator_id: 'c3',
    title: 'Neon Dreams',
    description: 'A cyberpunk animated short exploring identity in a world of digital consciousness.',
    thumbnail_url: 'https://picsum.photos/seed/neon/640/360',
    duration_seconds: 720,
    content_type: 'ANIMATION',
    monetization_type: 'FREE_NO_AD',
    ticket_price: null,
    creator: MOCK_CREATORS[2],
    view_count: 67300,
    like_count: 5120,
    comment_count: 445,
    published_at: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
    created_at: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
    status: 'PUBLISHED',
    tags: ['animation', 'cyberpunk', 'sci-fi'],
    quality_score: 88,
    made_with_studio: false,
  },
  {
    id: 'v4',
    creator_id: 'c4',
    title: 'The Weight of Silence',
    description: 'Two strangers meet on a train. Neither speaks the other\'s language. Yet they understand everything.',
    thumbnail_url: 'https://picsum.photos/seed/silence/640/360',
    duration_seconds: 1800,
    content_type: 'SHORT',
    monetization_type: 'FREE_AD',
    ticket_price: null,
    creator: MOCK_CREATORS[3],
    view_count: 89400,
    like_count: 7650,
    comment_count: 892,
    published_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
    created_at: new Date(Date.now() - 8 * 24 * 60 * 60 * 1000).toISOString(),
    status: 'PUBLISHED',
    tags: ['drama', 'romance', 'art house'],
    quality_score: 94,
    made_with_studio: true,
  },
  {
    id: 'v5',
    creator_id: 'c5',
    title: 'Binary Heart - Official Music Video',
    description: 'The official music video for "Binary Heart" by The Analog Kids.',
    thumbnail_url: 'https://picsum.photos/seed/binary/640/360',
    duration_seconds: 245,
    content_type: 'MUSIC_VIDEO',
    monetization_type: 'FREE_NO_AD',
    ticket_price: null,
    creator: MOCK_CREATORS[4],
    view_count: 234500,
    like_count: 18900,
    comment_count: 2341,
    published_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
    created_at: new Date(Date.now() - 14 * 24 * 60 * 60 * 1000).toISOString(),
    status: 'PUBLISHED',
    tags: ['music video', 'indie', 'electronic'],
    quality_score: 91,
    made_with_studio: false,
  },
  {
    id: 'v6',
    creator_id: 'c6',
    title: 'Forgotten Kingdoms - Episode 1: The First Light',
    description: 'The beginning of an epic fantasy series. When darkness falls, only the forgotten can save us.',
    thumbnail_url: 'https://picsum.photos/seed/kingdoms/640/360',
    duration_seconds: 2700,
    content_type: 'SERIES',
    monetization_type: 'SUBSCRIBER_ONLY',
    ticket_price: null,
    creator: MOCK_CREATORS[5],
    view_count: 178900,
    like_count: 14200,
    comment_count: 1876,
    published_at: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString(),
    created_at: new Date(Date.now() - 20 * 24 * 60 * 60 * 1000).toISOString(),
    status: 'PUBLISHED',
    tags: ['fantasy', 'series', 'epic'],
    quality_score: 95,
    made_with_studio: true,
  },
  {
    id: 'v7',
    creator_id: 'c1',
    title: 'Behind the Lens: Making of The Last Sunset',
    description: 'A deep dive into the creative process behind our award-winning short film.',
    thumbnail_url: 'https://picsum.photos/seed/behind/640/360',
    duration_seconds: 1320,
    content_type: 'OTHER',
    monetization_type: 'FREE_AD',
    ticket_price: null,
    creator: MOCK_CREATORS[0],
    view_count: 12300,
    like_count: 890,
    comment_count: 156,
    published_at: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
    created_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
    status: 'PUBLISHED',
    tags: ['documentary', 'behind the scenes', 'filmmaking'],
    quality_score: 82,
    made_with_studio: true,
  },
  {
    id: 'v8',
    creator_id: 'c2',
    title: 'City Lights, Lonely Nights',
    description: 'An intimate portrait of urban isolation in the modern age.',
    thumbnail_url: 'https://picsum.photos/seed/city/640/360',
    duration_seconds: 960,
    content_type: 'SHORT',
    monetization_type: 'FREE_AD',
    ticket_price: null,
    creator: MOCK_CREATORS[1],
    view_count: 56700,
    like_count: 4320,
    comment_count: 378,
    published_at: new Date(Date.now() - 4 * 24 * 60 * 60 * 1000).toISOString(),
    created_at: new Date(Date.now() - 12 * 24 * 60 * 60 * 1000).toISOString(),
    status: 'PUBLISHED',
    tags: ['drama', 'urban', 'mood piece'],
    quality_score: 89,
    made_with_studio: true,
  },
];

const getMockFeedItems = (feedType: FeedType): FeedItem[] => {
  const shuffled = [...MOCK_VIDEOS].sort(() => Math.random() - 0.5);

  const reasonMap: Record<FeedType, FeedItem['reason']> = {
    'for-you': 'recommended',
    'following': 'following',
    'trending': 'trending',
    'new': 'new',
  };

  return shuffled.map(video => ({
    video,
    reason: reasonMap[feedType],
  }));
};

// =============================================================================
// TYPES
// =============================================================================

type FeedType = 'for-you' | 'following' | 'trending' | 'new';

interface FeedState {
  // Feed items by type
  feeds: Record<FeedType, {
    items: FeedItem[];
    page: number;
    hasMore: boolean;
    isLoading: boolean;
    error: string | null;
  }>;

  // Active feed
  activeFeed: FeedType;

  // Search
  searchQuery: string;
  searchResults: Video[];
  searchLoading: boolean;
  searchPage: number;
  searchHasMore: boolean;

  // Categories
  categories: Array<{ id: string; name: string; count: number }>;

  // Actions
  setActiveFeed: (feed: FeedType) => void;
  loadFeed: (feedType?: FeedType, refresh?: boolean) => Promise<void>;
  loadMore: () => Promise<void>;
  refreshCurrentFeed: () => Promise<void>;

  // Search actions
  search: (query: string) => Promise<void>;
  loadMoreSearchResults: () => Promise<void>;
  clearSearch: () => void;

  // Category actions
  loadCategories: () => Promise<void>;
}

// =============================================================================
// INITIAL STATE
// =============================================================================

const createEmptyFeedState = () => ({
  items: [],
  page: 0,
  hasMore: true,
  isLoading: false,
  error: null,
});

// =============================================================================
// STORE
// =============================================================================

export const useFeedStore = create<FeedState>()((set, get) => ({
  // Initial state
  feeds: {
    'for-you': createEmptyFeedState(),
    'following': createEmptyFeedState(),
    'trending': createEmptyFeedState(),
    'new': createEmptyFeedState(),
  },

  activeFeed: 'for-you',

  searchQuery: '',
  searchResults: [],
  searchLoading: false,
  searchPage: 0,
  searchHasMore: true,

  categories: [],

  // Set active feed
  setActiveFeed: (feed) => {
    set({ activeFeed: feed });
    // Load feed if not already loaded
    const feedState = get().feeds[feed];
    if (feedState.items.length === 0 && !feedState.isLoading) {
      get().loadFeed(feed);
    }
  },

  // Load feed
  loadFeed: async (feedType, refresh = false) => {
    const type = feedType || get().activeFeed;
    const feedState = get().feeds[type];

    // Don't load if already loading
    if (feedState.isLoading) return;

    // Don't load if no more items and not refreshing
    if (!feedState.hasMore && !refresh) return;

    const page = refresh ? 1 : feedState.page + 1;

    set((state) => ({
      feeds: {
        ...state.feeds,
        [type]: {
          ...state.feeds[type],
          isLoading: true,
          error: null,
        },
      },
    }));

    try {
      let response: PaginatedResponse<FeedItem | Video>;

      switch (type) {
        case 'for-you':
          response = await api.getFeed(page);
          break;
        case 'following':
          // Following feed - would filter to followed creators
          response = await api.getFeed(page);
          break;
        case 'trending':
          const trendingVideos = await api.getTrending('24h', page);
          response = {
            ...trendingVideos,
            items: trendingVideos.items.map((video) => ({ video, reason: 'trending' as const })),
          };
          break;
        case 'new':
          const newVideos = await api.getNew(page);
          response = {
            ...newVideos,
            items: newVideos.items.map((video) => ({ video, reason: 'new' as const })),
          };
          break;
      }

      set((state) => ({
        feeds: {
          ...state.feeds,
          [type]: {
            items: refresh
              ? (response.items as FeedItem[])
              : [...state.feeds[type].items, ...(response.items as FeedItem[])],
            page,
            hasMore: response.has_more,
            isLoading: false,
            error: null,
          },
        },
      }));
    } catch (error) {
      // Use mock data when API is unavailable (development mode)
      const mockItems = getMockFeedItems(type);
      set((state) => ({
        feeds: {
          ...state.feeds,
          [type]: {
            items: refresh ? mockItems : [...state.feeds[type].items, ...mockItems],
            page,
            hasMore: false, // Mock data doesn't paginate
            isLoading: false,
            error: null,
          },
        },
      }));
    }
  },

  // Load more for current feed
  loadMore: async () => {
    await get().loadFeed();
  },

  // Refresh current feed
  refreshCurrentFeed: async () => {
    await get().loadFeed(get().activeFeed, true);
  },

  // Search
  search: async (query) => {
    if (!query.trim()) {
      set({
        searchQuery: '',
        searchResults: [],
        searchLoading: false,
        searchPage: 0,
        searchHasMore: true,
      });
      return;
    }

    set({
      searchQuery: query,
      searchLoading: true,
      searchPage: 1,
    });

    try {
      const response = await api.search(query, {}, 1);
      set({
        searchResults: response.items,
        searchHasMore: response.has_more,
        searchLoading: false,
      });
    } catch {
      // Use mock data for search when API is unavailable
      const lowerQuery = query.toLowerCase();
      const filteredVideos = MOCK_VIDEOS.filter(
        video =>
          video.title.toLowerCase().includes(lowerQuery) ||
          video.description.toLowerCase().includes(lowerQuery) ||
          video.tags.some(tag => tag.toLowerCase().includes(lowerQuery)) ||
          video.creator.display_name.toLowerCase().includes(lowerQuery)
      );
      set({
        searchResults: filteredVideos,
        searchHasMore: false,
        searchLoading: false,
      });
    }
  },

  // Load more search results
  loadMoreSearchResults: async () => {
    const { searchQuery, searchPage, searchHasMore, searchLoading } = get();

    if (!searchQuery || !searchHasMore || searchLoading) return;

    set({ searchLoading: true });

    try {
      const nextPage = searchPage + 1;
      const response = await api.search(searchQuery, {}, nextPage);
      set((state) => ({
        searchResults: [...state.searchResults, ...response.items],
        searchPage: nextPage,
        searchHasMore: response.has_more,
        searchLoading: false,
      }));
    } catch {
      set({ searchLoading: false });
    }
  },

  // Clear search
  clearSearch: () => {
    set({
      searchQuery: '',
      searchResults: [],
      searchLoading: false,
      searchPage: 0,
      searchHasMore: true,
    });
  },

  // Load categories
  loadCategories: async () => {
    try {
      const categories = await api.getCategories();
      set({ categories });
    } catch {
      // Ignore category load errors
    }
  },
}));

// =============================================================================
// SELECTORS
// =============================================================================

export const selectActiveFeed = (state: FeedState) => state.feeds[state.activeFeed];
export const selectFeedItems = (state: FeedState) => state.feeds[state.activeFeed].items;
export const selectIsLoading = (state: FeedState) => state.feeds[state.activeFeed].isLoading;
export const selectHasMore = (state: FeedState) => state.feeds[state.activeFeed].hasMore;

export default useFeedStore;
