package director

import "github.com/golden-shower-radio/station/internal/acquire"

// seedTracks is the built-in fallback wishlist used when no Anthropic key is
// configured (or when an LLM call fails). It is a diverse spread of real,
// well-known tracks across rock, soul, funk, electronic, hip-hop, reggae,
// jazz, afrobeat, and pop so the station can acquire and play immediately.
var seedTracks = []acquire.Query{
	// Rock / post-punk
	{Artist: "Fleetwood Mac", Title: "The Chain"},
	{Artist: "David Bowie", Title: "Ashes to Ashes"},
	{Artist: "Talking Heads", Title: "This Must Be the Place"},
	{Artist: "The Velvet Underground", Title: "Sunday Morning"},
	{Artist: "Radiohead", Title: "Weird Fishes / Arpeggi"},
	{Artist: "Joy Division", Title: "Atmosphere"},
	{Artist: "Pixies", Title: "Where Is My Mind?"},

	// Soul / funk
	{Artist: "Marvin Gaye", Title: "Inner City Blues"},
	{Artist: "Bill Withers", Title: "Ain't No Sunshine"},
	{Artist: "Curtis Mayfield", Title: "Move On Up"},
	{Artist: "Sly and the Family Stone", Title: "If You Want Me to Stay"},
	{Artist: "Aretha Franklin", Title: "Rock Steady"},
	{Artist: "The Isley Brothers", Title: "Footsteps in the Dark"},

	// Electronic
	{Artist: "Daft Punk", Title: "Something About Us"},
	{Artist: "Boards of Canada", Title: "Roygbiv"},
	{Artist: "Aphex Twin", Title: "Avril 14th"},
	{Artist: "Burial", Title: "Archangel"},
	{Artist: "Caribou", Title: "Can't Do Without You"},

	// Hip-hop
	{Artist: "A Tribe Called Quest", Title: "Electric Relaxation"},
	{Artist: "J Dilla", Title: "Don't Cry"},
	{Artist: "Madvillain", Title: "Accordion"},
	{Artist: "Nas", Title: "The World Is Yours"},

	// Reggae / dub
	{Artist: "Toots and the Maytals", Title: "Pressure Drop"},
	{Artist: "Augustus Pablo", Title: "King Tubby Meets Rockers Uptown"},
	{Artist: "Gregory Isaacs", Title: "Night Nurse"},

	// Jazz
	{Artist: "John Coltrane", Title: "Naima"},
	{Artist: "Bill Evans", Title: "Peace Piece"},
	{Artist: "Alice Coltrane", Title: "Journey in Satchidananda"},

	// Afrobeat / world / pop
	{Artist: "Fela Kuti", Title: "Water No Get Enemy"},
	{Artist: "Khruangbin", Title: "Maria También"},
	{Artist: "Sade", Title: "Cherish the Day"},
	{Artist: "Roy Ayers", Title: "Everybody Loves the Sunshine"},
}
