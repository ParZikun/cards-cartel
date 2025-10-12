import Image from 'next/image'

const getAttributeValue = (attributes, trait_type) => {
    if (!attributes || !Array.isArray(attributes)) {
        return 'N/A';
    }
    const attribute = attributes.find(attr => attr && attr.trait_type === trait_type);
    return attribute ? attribute.value : 'N/A';
};

export default function HoldingCard({ holding, priority }) {
    const grade = getAttributeValue(holding.attributes, 'The Grade');
    const gradingId = getAttributeValue(holding.attributes, 'Grading ID');

    return (
        <div className="card-glass card-glow rounded-xl shadow-lg flex flex-col transition-all duration-300" style={{'--glow-color': 'rgba(100, 116, 139, 0.4)', '--border-color': 'rgba(55, 65, 81, 1)', '--border-color-hover': 'rgba(100, 116, 139, 1)'}}>
            <div className="relative">
                <Image 
                    src={holding.image || 'https://placehold.co/300x420/0c0a15/2d3748?text=N/A'} 
                    alt={holding.name} 
                    width={300} 
                    height={420} 
                    className="h-72 w-full object-contain rounded-t-xl pt-4 bg-black/20" 
                    priority={priority} 
                    placeholder="blur" 
                    blurDataURL="data:image/gif;base64,R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw==" 
                />
            </div>
            
            <div className="p-4 flex flex-col flex-grow">
                <h3 className="font-bold text-white text-base leading-tight truncate mb-2" title={holding.name}>{holding.name}</h3>
                
                <div className="flex justify-between items-center text-sm text-gray-400">
                    <span className="font-semibold">Grade: {grade}</span>
                    <span className="font-mono text-xs">#{gradingId}</span>
                </div>
            </div>
        </div>
    )
}